import math
import csv
import os
import requests
from geopy.geocoders import Nominatim

API_KEY = "rr_osqvgdxsvqqt8fubacybdezqqgdtq6ja"
API_URL = "https://api.railradar.org/api/v1/trains/between"
geolocator = Nominatim(user_agent="smart_travel_india")
geo_cache = {}

def get_lat_lon(place):
    if place in geo_cache: return geo_cache[place]
    try:
        loc = geolocator.geocode(place + ", India", timeout=5)
        if loc:
            geo_cache[place] = (loc.latitude, loc.longitude)
            return geo_cache[place]
    except: pass
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
all_stations = []
junctions = []
small_stations = []

def load_national_stations():
    path = os.path.join(BASE_DIR, "all_india_stations.csv")
    if not os.path.exists(path): return
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                stn = {"code": r["code"].strip(), "name": r["Station"].strip(), "lat": float(r["Latitude"]), "lon": float(r["Longitude"])}
                all_stations.append(stn)
                if r.get("is_junction", "False").strip().lower() == "true": junctions.append(stn)
                else: small_stations.append(stn)
            except: continue

load_national_stations()

def find_nearest_station(lat, lon, station_list):
    nearest, min_dist = None, float("inf")
    for s in station_list:
        dist = haversine(lat, lon, s["lat"], s["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest = {"code": s["code"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], "distance_km": round(dist, 2)}
    return nearest

def get_trains(source, dest, date="2026-03-10", dist_km=0):
    from_lat, from_lon = get_lat_lon(source)
    to_lat, to_lon = get_lat_lon(dest)
    if dist_km == 0 and from_lat and to_lat: dist_km = haversine(from_lat, from_lon, to_lat, to_lon)
    if not from_lat or not to_lat: return []

    trains_found = []
    strategies = [
        (small_stations, small_stations, "Direct Local"),
        (small_stations, junctions, "Local to Junction"),
        (junctions, small_stations, "Junction to Local"),
        (junctions, junctions, "Express Junction")
    ]

    for src_list, dst_list, label in strategies:
        if trains_found: break 
        if not src_list or not dst_list: continue 
        src_stn = find_nearest_station(from_lat, from_lon, src_list)
        dst_stn = find_nearest_station(to_lat, to_lon, dst_list)
        if not src_stn or not dst_stn: continue
        if src_stn['distance_km'] > 150 or dst_stn['distance_km'] > 150: continue

        try:
            params = {"from": src_stn["code"], "to": dst_stn["code"], "date": date}
            res = requests.get(API_URL, headers={"X-API-Key": API_KEY}, params=params, timeout=8)
            data = res.json()
            raw_trains = data.get("trains") or data.get("data", {}).get("trains", [])

            if raw_trains:
                for t in raw_trains:
                    score = (t.get("avgSpeedKmph", 0) * 2) - (t.get("totalHalts", 0) * 2)
                    trains_found.append({
                        "type": "Train", "operator": f"{t.get('trainName')} ({t.get('trainNumber')})",
                        "bus_type": f"Via {src_stn['name']}", "depart": t.get("trainSrcDepartureTime", "00:00"),
                        "duration": round(t.get("travelTimeMinutes", 0) / 60, 1),
                        "price": 150 + int(t.get("distanceKm", 0) * 0.45),
                        "rating": "4.3", "punctuality": 88 if score > 50 else 65,
                        "icon": "🚆", "link": "https://www.irctc.co.in/nget/booking/train-list",
                        "src_stn_lat": src_stn["lat"], "src_stn_lon": src_stn["lon"], "src_stn_name": src_stn["name"],
                        "dst_stn_lat": dst_stn["lat"], "dst_stn_lon": dst_stn["lon"], "dst_stn_name": dst_stn["name"]
                    })
        except: continue

    if not trains_found and dist_km > 50:
        est_duration = round(dist_km / 55, 1) 
        trains_found = [{
            "type": "Train", "operator": "Connecting Trains", "bus_type": "Estimated Multi-Leg Journey",
            "depart": "Varies", "duration": est_duration, "price": f"{int(dist_km * 0.7)} - {int(dist_km * 1.6)}", 
            "rating": "4.0", "punctuality": 70, "icon": "🚆", "link": "https://www.irctc.co.in/",
            "tag": "🔄 Connecting Route Required"
        }]
    return trains_found