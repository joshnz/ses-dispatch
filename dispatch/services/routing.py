"""
OpenRouteService integration for travel time estimates.
Falls back to straight-line distance / 35 km/h when ORS is disabled.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def estimate_travel_time(origin_point, destination_point):
    """
    Estimate travel time in minutes between two GIS points.
    Uses ORS API if enabled, otherwise falls back to straight-line estimate.
    """
    if getattr(settings, "ORS_ENABLED", False) and getattr(settings, "ORS_API_KEY", ""):
        try:
            return _ors_travel_time(origin_point, destination_point)
        except Exception as e:
            logger.warning("ORS API failed, falling back to estimate: %s", e)

    return _straight_line_estimate(origin_point, destination_point)


def _straight_line_estimate(origin, destination):
    """Estimate travel minutes from straight-line distance at 35 km/h."""
    dist_degrees = origin.distance(destination)
    dist_km = dist_degrees * 111.32  # Approximate degrees to km
    return round((dist_km / 35) * 60, 1)


def _ors_travel_time(origin, destination):
    """Get travel time from OpenRouteService API."""
    import openrouteservice

    client = openrouteservice.Client(key=settings.ORS_API_KEY)
    coords = [
        [origin.x, origin.y],
        [destination.x, destination.y],
    ]
    result = client.directions(coords, profile="driving-car")
    duration_seconds = result["routes"][0]["summary"]["duration"]
    return round(duration_seconds / 60, 1)
