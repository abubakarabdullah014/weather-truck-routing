"""End-to-end: geocode → routes → weather@ETA → risk → recommend → heatmap."""
from __future__ import annotations

from datetime import datetime, timezone

from django.conf import settings

from .geocoding import GeocodingError, geocode
from .recommendation import recommend
from .risk import assess_checkpoint
from .routing import RoutingError, get_routes
from .weather import WeatherError, build_corridor_heatmap, fetch_hourly_grid, weather_at_eta


ALLOWED_INTERVALS = {10, 25, 50}


def _parse_departure(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("departure is required (ISO-8601).")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def plan_trip(
    origin_text: str,
    destination_text: str,
    departure_iso: str,
    load_weight_lb: float,
    sample_interval_miles: float | None = None,
) -> dict:
    if load_weight_lb < 0:
        raise ValueError("load_weight must be >= 0.")

    interval = float(
        sample_interval_miles
        if sample_interval_miles is not None
        else settings.DEFAULT_SAMPLE_INTERVAL_MILES
    )
    # Snap to allowed 10 / 25 / 50
    if interval not in ALLOWED_INTERVALS:
        interval = min(ALLOWED_INTERVALS, key=lambda x: abs(x - interval))

    departure = _parse_departure(departure_iso)

    origin = geocode(origin_text)
    destination = geocode(destination_text)

    routes = get_routes(origin, destination, interval)
    if not routes:
        raise RoutingError("No routes found between origin and destination.")

    # Gather all checkpoints for a single batched weather call
    flat_points = []
    index_map: list[tuple[int, int]] = []  # (route_idx, cp_idx)
    for ri, route in enumerate(routes):
        for ci, cp in enumerate(route["checkpoints"]):
            flat_points.append({"lat": cp["lat"], "lon": cp["lon"]})
            index_map.append((ri, ci))

    # Cover full trip duration + buffer (up to 48h forecast window)
    max_offset = max(
        (cp["eta_offset_s"] for r in routes for cp in r["checkpoints"]),
        default=0,
    )
    hours_needed = min(48, max(24, int(max_offset / 3600) + 6))

    weather_grid = fetch_hourly_grid(flat_points, departure, hours=hours_needed)

    for (ri, ci), wx in zip(index_map, weather_grid):
        cp = routes[ri]["checkpoints"][ci]
        eta = departure.timestamp() + cp["eta_offset_s"]
        from datetime import datetime as dt

        eta_dt = dt.fromtimestamp(eta, tz=timezone.utc)
        conditions = weather_at_eta(wx.get("hourly", []), eta_dt)
        assessment = assess_checkpoint(
            conditions["wind_mph"],
            conditions["rain_in_hr"],
            conditions["snow_in_hr"],
            load_weight_lb,
        )
        cp.update(conditions)
        cp.update(assessment)
        cp["eta"] = eta_dt.isoformat()

    recommendation = recommend(routes)

    heatmap = build_corridor_heatmap(routes, departure, hours=48)

    return {
        "origin": origin,
        "destination": destination,
        "departure": departure.isoformat(),
        "load_weight_lb": load_weight_lb,
        "sample_interval_miles": interval,
        "routes": routes,
        "recommendation": recommendation,
        "heatmap": heatmap,
    }


__all__ = [
    "plan_trip",
    "GeocodingError",
    "RoutingError",
    "WeatherError",
]
