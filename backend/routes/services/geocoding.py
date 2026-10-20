"""Geocode place names to lat/lon via Nominatim."""
from __future__ import annotations

import requests
from django.conf import settings


class GeocodingError(Exception):
    pass


def geocode(query: str) -> dict:
    """
    Resolve a free-text place name to coordinates.
    Returns {lat, lon, display_name}.
    """
    query = (query or "").strip()
    if not query:
        raise GeocodingError("Origin/destination cannot be empty.")

    # Accept "lat,lon" directly
    if "," in query:
        parts = [p.strip() for p in query.split(",")]
        if len(parts) == 2:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return {
                        "lat": lat,
                        "lon": lon,
                        "display_name": f"{lat:.5f}, {lon:.5f}",
                    }
            except ValueError:
                pass

    url = f"{settings.NOMINATIM_BASE_URL}/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": settings.GEOCODER_USER_AGENT}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise GeocodingError(f"Geocoding failed for '{query}': {exc}") from exc

    if not data:
        raise GeocodingError(f"No results found for '{query}'.")

    hit = data[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "display_name": hit.get("display_name", query),
    }
