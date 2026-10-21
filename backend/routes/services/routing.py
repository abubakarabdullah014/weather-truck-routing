"""Fetch up to 3 distinct driving route options via ORS / OSRM / via-points."""
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

        while next_mark <= cumulative + seg + 1e-6:
            t = (next_mark - cumulative) / seg
            t = min(max(t, 0.0), 1.0)
            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t
            miles = next_mark / METERS_PER_MILE
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


def _midpoint(coords: list[list[float]]) -> tuple[float, float]:
    if not coords:
        return (0.0, 0.0)
    mid = coords[len(coords) // 2]
    return (mid[0], mid[1])


def _routes_similar(a: dict, b: dict) -> bool:
    """
    True when two routes follow essentially the same corridor
    (similar length AND midpoints within ~25 km).
    """
    if abs(a["distance_miles"] - b["distance_miles"]) > 40:
        return False
    ma = _midpoint(a.get("coordinates") or [])
    mb = _midpoint(b.get("coordinates") or [])
    return _haversine_m(ma[0], ma[1], mb[0], mb[1]) < 25_000


def _offset_point(
    lat: float, lon: float, bearing_deg: float, distance_m: float
) -> dict:
    """Move from lat/lon along bearing by distance_m (spherical)."""
    r = 6371000.0
    br = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    ang = distance_m / r
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang)
        + math.cos(lat1) * math.sin(ang) * math.cos(br)
    )
    lon2 = lon1 + math.atan2(
        math.sin(br) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return {"lat": math.degrees(lat2), "lon": math.degrees(lon2)}


def _corridor_via_points(origin: dict, destination: dict) -> list[dict]:
    """
    Build left/right waypoints near the trip midpoint so we can force
    distinct corridor options when APIs return fewer than 3 alternatives.
    """
    lat1, lon1 = origin["lat"], origin["lon"]
    lat2, lon2 = destination["lat"], destination["lon"]
    mid_lat = (lat1 + lat2) / 2.0
    mid_lon = (lon1 + lon2) / 2.0
    # Bearing origin→dest, then ±90° for perpendicular offsets
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(dlon)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    # Offset ~8% of trip length, capped (keeps vias on a useful detour)
    trip_m = _haversine_m(lat1, lon1, lat2, lon2)
    offset_m = min(max(trip_m * 0.08, 15_000), 80_000)
    return [
        _offset_point(mid_lat, mid_lon, (bearing + 90) % 360, offset_m),
        _offset_point(mid_lat, mid_lon, (bearing - 90) % 360, offset_m),
    ]


def _fetch_ors(origin: dict, destination: dict, via: dict | None = None) -> list[dict]:
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY not configured")

    url = f"{settings.ORS_BASE_URL}/v2/directions/driving-hgv"
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }
    coords = [[origin["lon"], origin["lat"]]]
    if via:
        coords.append([via["lon"], via["lat"]])
    coords.append([destination["lon"], destination["lat"]])

    body: dict[str, Any] = {
        "coordinates": coords,
        "instructions": False,
        "geometry": True,
    }
    if via is None:
        body["alternative_routes"] = {
            "target_count": 3,
            "share_factor": 0.6,
            "weight_factor": 1.4,
        }

    resp = requests.post(url, json=body, headers=headers, timeout=45)
    if resp.status_code >= 400 and "alternative_routes" in body:
        body.pop("alternative_routes", None)
        resp = requests.post(url, json=body, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    routes_out: list[dict] = []
    for idx, feature in enumerate(data.get("routes", data.get("features", []))):
        if "geometry" in feature and isinstance(feature["geometry"], str):
            path = _decode_polyline(feature["geometry"], precision=5)
            summary = feature.get("summary", {})
            duration = summary.get("duration", feature.get("duration", 0))
            distance = summary.get("distance", feature.get("distance", 0))
        elif "geometry" in feature and isinstance(feature["geometry"], dict):
            raw = feature["geometry"].get("coordinates", [])
            path = [[c[1], c[0]] for c in raw]
            props = feature.get("properties", {}).get("summary", {})
            duration = props.get("duration", 0)
            distance = props.get("distance", 0)
        else:
            continue

        routes_out.append(
            {
                "id": idx + 1,
                "label": f"Route {idx + 1}",
                "coordinates": path,
                "distance_m": float(distance),
                "distance_miles": round(float(distance) / METERS_PER_MILE, 2),
                "duration_s": float(duration),
                "provider": "openrouteservice",
            }
        )
    return routes_out


def _fetch_osrm(
    origin: dict, destination: dict, via: dict | None = None
) -> list[dict]:
    parts = [f"{origin['lon']},{origin['lat']}"]
    if via:
        parts.append(f"{via['lon']},{via['lat']}")
    parts.append(f"{destination['lon']},{destination['lat']}")
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/" + ";".join(parts)
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "true" if via is None else "false",
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
        path = [[c[1], c[0]] for c in raw]
        distance = float(route["distance"])
        duration = float(route["duration"])
        routes_out.append(
            {
                "id": idx + 1,
                "label": f"Route {idx + 1}",
                "coordinates": path,
                "distance_m": distance,
                "distance_miles": round(distance / METERS_PER_MILE, 2),
                "duration_s": duration,
                "provider": "osrm",
            }
        )
    return routes_out


def _merge_unique(pool: list[dict], candidates: list[dict], limit: int = 3) -> list[dict]:
    for candidate in candidates:
        if len(pool) >= limit:
            break
        if any(_routes_similar(candidate, existing) for existing in pool):
            continue
        pool.append(candidate)
    return pool


def get_routes(
    origin: dict, destination: dict, sample_interval_miles: float
) -> list[dict]:
    """
    Return up to 3 distinct routes with sampled checkpoint skeletons.

    Strategy:
      1. ORS alternatives (when allowed)
      2. OSRM alternatives
      3. Forced via-point detours (left/right of corridor) to fill to 3
    """
    routes: list[dict] = []
    errors: list[str] = []

    if settings.ORS_API_KEY:
        try:
            routes = _merge_unique(routes, _fetch_ors(origin, destination))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ORS: {exc}")

    if len(routes) < 3:
        try:
            routes = _merge_unique(routes, _fetch_osrm(origin, destination))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OSRM: {exc}")

    # Force corridor diversity with via waypoints until we have 3
    if len(routes) < 3:
        for via in _corridor_via_points(origin, destination):
            if len(routes) >= 3:
                break
            try:
                if settings.ORS_API_KEY:
                    routes = _merge_unique(
                        routes, _fetch_ors(origin, destination, via=via)
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"ORS-via: {exc}")
            if len(routes) >= 3:
                break
            try:
                routes = _merge_unique(
                    routes, _fetch_osrm(origin, destination, via=via)
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"OSRM-via: {exc}")

    if not routes:
        raise RoutingError("Could not fetch routes. " + "; ".join(errors))

    routes = routes[:3]
    for idx, route in enumerate(routes):
        route["id"] = idx + 1
        route["label"] = f"Route {idx + 1}"
        full_coords = route["coordinates"]
        route["checkpoints"] = _sample_along_route(full_coords, sample_interval_miles)
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
