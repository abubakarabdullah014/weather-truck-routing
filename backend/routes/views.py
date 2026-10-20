from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.geocoding import GeocodingError
from .services.pipeline import plan_trip
from .services.routing import RoutingError
from .services.weather import WeatherError


@api_view(["GET"])
def health(request):
    """Liveness checkpoint — polled by Vercel cron every 5 minutes."""
    return Response(
        {
            "status": "ok",
            "service": "weather-truck-routing",
            "checkpoint": "health",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing": "ors" if settings.ORS_API_KEY else "osrm",
        }
    )


@api_view(["POST"])
def plan(request):
    """
    Body:
      origin: str
      destination: str
      departure: ISO-8601 datetime
      load_weight: number (lb)
      sample_interval_miles: 10 | 25 | 50 (optional)
    """
    data = request.data or {}
    origin = data.get("origin", "")
    destination = data.get("destination", "")
    departure = data.get("departure", "")
    load_weight = data.get("load_weight", data.get("load_weight_lb"))
    interval = data.get("sample_interval_miles")

    if not origin or not destination:
        return Response(
            {"error": "origin and destination are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        load_weight = float(load_weight)
    except (TypeError, ValueError):
        return Response(
            {"error": "load_weight must be a number (pounds)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = plan_trip(
            origin_text=str(origin),
            destination_text=str(destination),
            departure_iso=str(departure),
            load_weight_lb=load_weight,
            sample_interval_miles=float(interval) if interval is not None else None,
        )
    except (GeocodingError, RoutingError, WeatherError, ValueError) as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:  # noqa: BLE001
        return Response(
            {"error": f"Unexpected server error: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Slim polyline for client payload size (keep full for map; already needed)
    return Response(result)
