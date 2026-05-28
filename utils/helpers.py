import requests
from config.constants import NORTHEAST_STATES, GEOAPIFY_KEY

def get_state(lat, lon):
    for s, b in NORTHEAST_STATES.items():
        if b["south"] <= lat <= b["north"] and b["west"] <= lon <= b["east"]:
            return s
    return None

def in_ne(lat, lon):
    return get_state(lat, lon) is not None

def geocode(place):
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {"text": place, "apiKey": GEOAPIFY_KEY, "limit": 1}
    data = requests.get(url, params=params).json()
    coords = data["features"][0]["geometry"]["coordinates"]
    return (coords[1], coords[0])

# ⭐ IMPORTANT FIX
def is_north_of_siliguri(lat, lon):
    return lat > 26.7   # Above Siliguri → no backward routing

def format_time(sec):
    h = int(sec)//3600
    m = (int(sec)%3600)//60
    return f"{h}h {m}m" if h else f"{m} mins"

def fare(dist):
    return round(50 + dist*14)
