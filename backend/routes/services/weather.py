"""Fetch hourly weather forecasts from Open-Meteo."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from django.conf import settings


class WeatherError(Exception):
    pass


# Open-Meteo: precipitation mm, snowfall cm, wind km/h → convert to imperial
MM_TO_IN = 1 / 25.4
CM_TO_IN = 1 / 2.54
KMH_TO_MPH = 0.621371


def _parse_iso(ts: str) -> datetime:
    # Open-Meteo returns "2026-10-21T14:00" (no tz) — treat as UTC
    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_hourly_grid(
    points: list[dict[str, float]],
    start: datetime,
    hours: int = 48,
) -> list[dict[str, Any]]:
    """
    Batch-fetch hourly weather for many lat/lon points.
    Returns list aligned with `points`, each with hourly series.
    """
    if not points:
        return []

    # Cap batch size; Open-Meteo supports multi-location via comma lists
    results: list[dict[str, Any]] = [{} for _ in points]
    chunk_size = 40

    end = start + timedelta(hours=hours + 1)
    start_date = start.astimezone(timezone.utc).date().isoformat()
    end_date = end.astimezone(timezone.utc).date().isoformat()

    for offset in range(0, len(points), chunk_size):
        chunk = points[offset : offset + chunk_size]
        lats = ",".join(f"{p['lat']:.5f}" for p in chunk)
        lons = ",".join(f"{p['lon']:.5f}" for p in chunk)
        params = {
            "latitude": lats,
            "longitude": lons,
            "hourly": "precipitation,snowfall,wind_speed_10m",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_date": start_date,
            "end_date": end_date,
        }
        try:
            resp = requests.get(
                settings.OPEN_METEO_BASE_URL, params=params, timeout=40
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            raise WeatherError(f"Weather API error: {exc}") from exc

        # Single location → dict; multi → list
        entries = payload if isinstance(payload, list) else [payload]
        for i, entry in enumerate(entries):
            hourly = entry.get("hourly", {})
            times = hourly.get("time", [])
            precip = hourly.get("precipitation", [])
            snow = hourly.get("snowfall", [])
            wind = hourly.get("wind_speed_10m", [])
            series = []
            for j, t in enumerate(times):
                series.append(
                    {
                        "time": t,
                        "rain_in_hr": float(precip[j] or 0) if j < len(precip) else 0.0,
                        # Open-Meteo snowfall with precipitation_unit=inch → inches
                        "snow_in_hr": float(snow[j] or 0) if j < len(snow) else 0.0,
                        "wind_mph": float(wind[j] or 0) if j < len(wind) else 0.0,
                    }
                )
            results[offset + i] = {"hourly": series}

    return results


def weather_at_eta(
    hourly: list[dict], eta: datetime
) -> dict[str, float]:
    """Pick the hourly bucket closest to the estimated arrival time."""
    if not hourly:
        return {"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}

    best = min(
        hourly,
        key=lambda h: abs((_parse_iso(h["time"]) - eta).total_seconds()),
    )
    return {
        "wind_mph": round(best["wind_mph"], 2),
        "rain_in_hr": round(best["rain_in_hr"], 3),
        "snow_in_hr": round(best["snow_in_hr"], 3),
        "forecast_time": best["time"],
    }


def build_corridor_heatmap(
    routes: list[dict],
    departure: datetime,
    hours: int = 48,
) -> dict[str, Any]:
    """
    Build a coarse weather grid along the trip corridor for the heatmap slider.
    Samples every ~N-th coordinate across all routes, then fetches hourly data.
    """
    # Collect unique-ish points from all route polylines
    samples: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for route in routes:
        coords = route.get("coordinates") or []
        step = max(1, len(coords) // 40)
        for i in range(0, len(coords), step):
            lat, lon = coords[i]
            key = (int(lat * 50), int(lon * 50))  # ~0.02° buckets
            if key in seen:
                continue
            seen.add(key)
            samples.append({"lat": lat, "lon": lon})
        # Always include end
        if coords:
            lat, lon = coords[-1]
            key = (int(lat * 50), int(lon * 50))
            if key not in seen:
                seen.add(key)
                samples.append({"lat": lat, "lon": lon})

    if not samples:
        return {"hours": hours, "points": []}

    grid = fetch_hourly_grid(samples, departure, hours=hours)
    points_out = []
    for sample, wx in zip(samples, grid):
        points_out.append(
            {
                "lat": sample["lat"],
                "lon": sample["lon"],
                "hourly": wx.get("hourly", []),
            }
        )
    return {"hours": hours, "points": points_out}
