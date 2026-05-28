
import requests
from functools import lru_cache

# ─── Cache for fixed gateway segments ───
_segment_cache = {}

def _cache_key(start, end):
    """Create a hashable cache key from coordinate tuples."""
    return (round(start[0], 4), round(start[1], 4),
            round(end[0], 4), round(end[1], 4))

def get_route_data(start, end):
    """
    Get route data from OSRM API with caching and timeout.
    Returns: (route_coordinates, distance_km, duration_seconds)
    """
    key = _cache_key(start, end)

    # Return cached result if available
    if key in _segment_cache:
        print(f"CACHE HIT: {start} -> {end}")
        return _segment_cache[key]

    url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    data = requests.get(url, params=params, timeout=15).json()

    if data.get("code") != "Ok":
        raise ValueError(f"Route not found: {data.get('message', 'Unknown error')}")

    coords = data["routes"][0]["geometry"]["coordinates"]
    distance = data["routes"][0]["distance"] / 1000
    duration = data["routes"][0]["duration"]

    route = [(lat, lon) for lon, lat in coords]
    result = (route, round(distance, 2), duration)

    # Cache the result
    _segment_cache[key] = result
    print(f"CACHED: {start} -> {end} ({round(distance, 1)} km)")

    return result


def preload_gateway_segments():
    """
    Pre-cache fixed gateway-to-gateway segments at app startup.
    These routes never change, so we only fetch them once.
    """
    from config.constants import ISLAMPUR, SILIGURI, SILCHAR, PILIBHIT, LUCKNOW

    fixed_pairs = [
        (ISLAMPUR, SILIGURI),
        (SILIGURI, ISLAMPUR),
        (SILIGURI, SILCHAR),
        (SILCHAR, SILIGURI),
        (PILIBHIT, ISLAMPUR),
        (ISLAMPUR, PILIBHIT),
        (LUCKNOW, ISLAMPUR),
        (ISLAMPUR, LUCKNOW),
    ]

    print("Pre-loading gateway segments...")
    for start, end in fixed_pairs:
        try:
            get_route_data(start, end)
        except Exception as e:
            print(f"Failed to preload {start} -> {end}: {e}")
    print("Gateway segments cached!")
