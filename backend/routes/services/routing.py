"""Fetch up to 3 driving route alternatives via ORS or OSRM."""
from __future__ import annotations

import math
from typing import Any

import requests
from django.conf import settings

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _decode_polyline(encoded: str, precision: int = 5) -> list[list[float]]:
    """Decode Google Encoded Polyline (ORS uses precision 5)."""
    coords: list[list[float]] = []
    index = 0
    lat = 0
    lon = 0
    length = len(encoded)
    factor = 10**precision

    while index < length:
        for coord_is_lat in (True, False):
            result = 0
            shift = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if coord_is_lat:
                lat += delta
            else:
                lon += delta
        coords.append([lat / factor, lon / factor])
    return coords


def _sample_along_route(
    coordinates: list[list[float]], interval_miles: float
) -> list[dict[str, Any]]:
    """
    Walk the polyline and emit checkpoints every `interval_miles`,
    plus the destination. Each point: {lat, lon, distance_miles, distance_m}.
    """
    if not coordinates:
        return []

    interval_m = max(interval_miles, 1.0) * METERS_PER_MILE
    checkpoints: list[dict[str, Any]] = []
    cumulative = 0.0
    next_mark = 0.0

    # Always include origin
    checkpoints.append(
        {
            "lat": coordinates[0][0],
            "lon": coordinates[0][1],
            "distance_miles": 0.0,
            "distance_m": 0.0,
        }
    )
    next_mark = interval_m

    for i in range(1, len(coordinates)):
        lat1, lon1 = coordinates[i - 1]
        lat2, lon2 = coordinates[i]
        seg = _haversine_m(lat1, lon1, lat2, lon2)
        if seg <= 0:
            continue

        # Place marks that fall within this segment
        while next_mark <= cumulative + seg + 1e-6:
            t = (next_mark - cumulative) / seg
            t = min(max(t, 0.0), 1.0)
            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t
            miles = next_mark / METERS_PER_MILE
            # Avoid duplicating origin
            if miles > 0.05:
                checkpoints.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "distance_miles": round(miles, 2),
                        "distance_m": round(next_mark, 1),
                    }
                )
            next_mark += interval_m

        cumulative += seg

    # Ensure destination is present
    last = coordinates[-1]
    total_miles = cumulative / METERS_PER_MILE
    if (
        not checkpoints
        or abs(checkpoints[-1]["lat"] - last[0]) > 1e-5
        or abs(checkpoints[-1]["lon"] - last[1]) > 1e-5
    ):
        checkpoints.append(
            {
                "lat": last[0],
                "lon": last[1],
                "distance_miles": round(total_miles, 2),
                "distance_m": round(cumulative, 1),
            }
        )
    else:
        checkpoints[-1]["distance_miles"] = round(total_miles, 2)
        checkpoints[-1]["distance_m"] = round(cumulative, 1)

    return checkpoints


def _fetch_ors(origin: dict, destination: dict) -> list[dict]:
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY not configured")

    url = f"{settings.ORS_BASE_URL}/v2/directions/driving-hgv"
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [
            [origin["lon"], origin["lat"]],
            [destination["lon"], destination["lat"]],
        ],
        "alternative_routes": {
            "target_count": 3,
            "share_factor": 0.6,
            "weight_factor": 1.4,
        },
        "instructions": False,
        "geometry": True,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=45)
    if resp.status_code >= 400:
        # Retry without alternatives (some keys/plans reject them)
        body.pop("alternative_routes", None)
        resp = requests.post(url, json=body, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    routes_out: list[dict] = []
    for idx, feature in enumerate(data.get("routes", data.get("features", []))):
        # ORS directions JSON vs GeoJSON response shapes
        if "geometry" in feature and isinstance(feature["geometry"], str):
            coords = _decode_polyline(feature["geometry"], precision=5)
            summary = feature.get("summary", {})
            duration = summary.get("duration", feature.get("duration", 0))
            distance = summary.get("distance", feature.get("distance", 0))
        elif "geometry" in feature and isinstance(feature["geometry"], dict):
            # GeoJSON [lon, lat]
            raw = feature["geometry"].get("coordinates", [])
            coords = [[c[1], c[0]] for c in raw]
            props = feature.get("properties", {}).get("summary", {})
            duration = props.get("duration", 0)
            distance = props.get("distance", 0)
        else:
            continue

        routes_out.append(
            {
                "id": idx + 1,
                "label": f"Route {idx + 1}",
                "coordinates": coords,
                "distance_m": float(distance),
                "distance_miles": round(float(distance) / METERS_PER_MILE, 2),
                "duration_s": float(duration),
                "provider": "openrouteservice",
            }
        )
    return routes_out


def _fetch_osrm(origin: dict, destination: dict) -> list[dict]:
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{origin['lon']},{origin['lat']};{destination['lon']},{destination['lat']}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "true",
        "steps": "false",
    }
    resp = requests.get(url, params=params, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RoutingError(data.get("message", "OSRM routing failed"))

    routes_out: list[dict] = []
    for idx, route in enumerate(data.get("routes", [])[:3]):
        raw = route["geometry"]["coordinates"]
        coords = [[c[1], c[0]] for c in raw]
        distance = float(route["distance"])
        duration = float(route["duration"])
        routes_out.append(
            {
                "id": idx + 1,
                "label": f"Route {idx + 1}",
                "coordinates": coords,
                "distance_m": distance,
                "distance_miles": round(distance / METERS_PER_MILE, 2),
                "duration_s": duration,
                "provider": "osrm",
            }
        )
    return routes_out


def _routes_similar(a: dict, b: dict, tol_miles: float = 8.0) -> bool:
    """Treat routes as duplicates when length is nearly identical."""
    return abs(a["distance_miles"] - b["distance_miles"]) < tol_miles


def get_routes(
    origin: dict, destination: dict, sample_interval_miles: float
) -> list[dict]:
    """
    Return up to 3 routes with sampled checkpoint skeletons
    (weather/risk filled in later).

    Prefers OpenRouteService; supplements with OSRM alternatives when ORS
    returns fewer than 3 (common on free tier for longer hauls).
    """
    routes: list[dict] = []
    errors: list[str] = []

    if settings.ORS_API_KEY:
        try:
            routes = _fetch_ors(origin, destination)
        except Exception as exc:  # noqa: BLE001 — fall back / supplement via OSRM
            errors.append(f"ORS: {exc}")

    if len(routes) < 3:
        try:
            osrm_routes = _fetch_osrm(origin, destination)
            if not routes:
                routes = osrm_routes
            else:
                for candidate in osrm_routes:
                    if len(routes) >= 3:
                        break
                    if any(_routes_similar(candidate, existing) for existing in routes):
                        continue
                    routes.append(candidate)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OSRM: {exc}")
            if not routes:
                raise RoutingError(
                    "Could not fetch routes. " + "; ".join(errors)
                ) from exc

    routes = routes[:3]
    for idx, route in enumerate(routes):
        route["id"] = idx + 1
        route["label"] = f"Route {idx + 1}"
        full_coords = route["coordinates"]
        route["checkpoints"] = _sample_along_route(full_coords, sample_interval_miles)
        # Downsample dense polylines for map performance (after sampling)
        route["coordinates"] = _downsample_coords(full_coords, max_points=800)
        total_dist = route["distance_m"] or 1.0
        total_dur = route["duration_s"] or 1.0
        for cp in route["checkpoints"]:
            frac = cp["distance_m"] / total_dist
            cp["eta_offset_s"] = round(frac * total_dur)

    return routes


def _downsample_coords(
    coordinates: list[list[float]], max_points: int = 800
) -> list[list[float]]:
    if len(coordinates) <= max_points:
        return coordinates
    step = max(1, len(coordinates) // max_points)
    out = coordinates[::step]
    if out[-1] != coordinates[-1]:
        out.append(coordinates[-1])
    return out
