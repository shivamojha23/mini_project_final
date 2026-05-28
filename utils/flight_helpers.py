import csv, math, time, os
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="multimodal_travel")
geo_cache  = {}

def get_lat_lon(place):
    if place in geo_cache:
        return geo_cache[place]
    try:
        loc = geolocator.geocode(place + ", India", timeout=10)
        time.sleep(1)
        if loc:
            geo_cache[place] = (loc.latitude, loc.longitude)
            return geo_cache[place]
    except:
        pass
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def load_airports(csv_file):
    airports = []
    if not os.path.exists(csv_file):
        return airports
    with open(csv_file, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                if r["iso_country"] == "IN" and r["iata_code"].strip():
                    airports.append({
                        "code": r["iata_code"].strip(),
                        "name": r["name"].strip(),
                        "lat":  float(r["latitude_deg"]),
                        "lon":  float(r["longitude_deg"])
                    })
            except:
                continue
    return airports

airports = load_airports("airports.csv")

def find_nearest_airport(lat, lon):
    if not airports:
        return None
    return min(airports, key=lambda a: haversine(lat, lon, a["lat"], a["lon"]))
