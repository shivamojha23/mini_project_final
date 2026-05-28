import requests

GEOAPIFY_KEY = "57e420cd91b64223bc484b98e702f0df"

KNOWN_PLACES = {
    "medicaps university": (22.6212, 75.8043),
    "medicaps university indore": (22.6212, 75.8043),
    "medicaps": (22.6212, 75.8043),
    "iit indore": (22.5200, 75.9200),
    "iim indore": (22.6786, 75.9369),
    "devi ahilya university": (22.7166, 75.8781),
    "indore airport": (22.7217, 75.8015),
    "rajwada indore": (22.7196, 75.8577),
}


def city_to_coords(place):
    """
    Convert place name to coordinates
    Checks: raw coordinates -> KNOWN_PLACES -> Geoapify API
    Returns: (latitude, longitude)
    """
    place = place.strip()
    
    # Handle raw coordinates like "22.7196, 75.8577"
    try:
        parts = place.split(",")
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                print(f"Parsed as coordinates: {lat}, {lon}")
                return lat, lon
    except (ValueError, AttributeError):
        pass
    
    # Check KNOWN_PLACES first
    key = place.lower()
    if key in KNOWN_PLACES:
        coords = KNOWN_PLACES[key]
        print(f"Found in KNOWN_PLACES: {place} -> {coords}")
        return coords
    
    # Try Geoapify API
    print(f"Searching Geoapify for: {place}")
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": place,
        "apiKey": GEOAPIFY_KEY,
        "filter": "countrycode:in",
        "limit": 1,
        "lang": "en"
    }
    
    try:
        data = requests.get(url, params=params, timeout=5).json()
        print("GEOAPIFY RESPONSE:", data)
        
        if data.get("features"):
            coords = data["features"][0]["geometry"]["coordinates"]
            result = (coords[1], coords[0])
            print(f"Found via Geoapify: {place} -> {result}")
            return result
    
    except requests.exceptions.Timeout:
        raise ValueError(f"Geoapify timeout for: {place}")
    except Exception as e:
        raise ValueError(f"Geoapify error: {str(e)}")
    
    raise ValueError(f"Location not found: {place}")

