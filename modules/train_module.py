# train_module.py

from geopy.geocoders import Nominatim
import csv
import math
import time
import requests
import pandas as pd

# ==================================================
# CONFIG
# ==================================================
API_URL = "https://api.railradar.org/api/v1/trains/between"
API_KEY = "rr_6ilyrx3lm3vewaa53nhqtzz81fjv4jmc"

geolocator = Nominatim(user_agent="railway_station_finder")

# ==================================================
# GEO CACHE
# ==================================================
geo_cache = {}

def get_lat_lon(place):
    if place in geo_cache:
        return geo_cache[place]

    try:
        loc = geolocator.geocode(place, timeout=10)
        time.sleep(1)

        if loc:
            geo_cache[place] = (loc.latitude, loc.longitude)
            return geo_cache[place]
    except:
        pass

    return None, None


# ==================================================
# HAVERSINE DISTANCE
# ==================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ==================================================
# LOAD STATIONS
# ==================================================
def load_stations(csv_file):
    stations = []

    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for r in reader:
            try:
                stations.append({
                    "code": r["code"].strip(),
                    "name": r["Station"].strip(),
                    "lat": float(r["Latitude"]),
                    "lon": float(r["Longitude"])
                })
            except:
                continue

    return stations


# ==================================================
# FIND NEAREST STATION
# ==================================================
def find_nearest(lat, lon, station_list):
    nearest = None
    min_dist = float("inf")

    for s in station_list:
        dist = haversine(lat, lon, s["lat"], s["lon"])

        if dist < min_dist:
            min_dist = dist
            nearest = {
                "code": s["code"],
                "name": s["name"],
                "distance_km": round(dist, 2)
            }

    return nearest


def nearest_junctions(lat, lon, junction_list, limit=10):
    arr = []

    for s in junction_list:
        dist = haversine(lat, lon, s["lat"], s["lon"])

        arr.append({
            "code": s["code"],
            "name": s["name"],
            "lat": s["lat"],
            "lon": s["lon"],
            "distance": dist
        })

    arr = sorted(arr, key=lambda x: x["distance"])
    return arr[:limit]


# ==================================================
# MAIN LOGIC FUNCTION (IMPORTANT)
# ==================================================
def get_best_trains(from_place, to_place, date,
                    small_stations, junction_stations):

    from_lat, from_lon = get_lat_lon(from_place)
    to_lat, to_lon = get_lat_lon(to_place)

    if not from_lat or not to_lat:
        return None, None, [], [], "Place not found"

    headers = {"X-API-Key": API_KEY}

    trains = []
    route_mode = ""
    from_station = None
    to_station = None

    # STEP 1: SMALL → SMALL
    from_small = find_nearest(from_lat, from_lon, small_stations)
    to_small = find_nearest(to_lat, to_lon, small_stations)

    params = {
        "from": from_small["code"],
        "to": to_small["code"],
        "date": date
    }

    res = requests.get(API_URL, headers=headers, params=params, timeout=15)
    data = res.json()
    trains = data.get("trains") or data.get("data", {}).get("trains", [])

    if trains:
        route_mode = "Small → Small"
        from_station = from_small
        to_station = to_small

    # STEP 2: SMALL → JUNCTION
    if not trains:
        to_junction = find_nearest(to_lat, to_lon, junction_stations)

        params = {
            "from": from_small["code"],
            "to": to_junction["code"],
            "date": date
        }

        res = requests.get(API_URL, headers=headers, params=params, timeout=15)
        data = res.json()
        trains = data.get("trains") or data.get("data", {}).get("trains", [])

        if trains:
            route_mode = "Small → Junction"
            from_station = from_small
            to_station = to_junction

    # STEP 3: JUNCTION → SMALL
    if not trains:
        from_junction = find_nearest(from_lat, from_lon, junction_stations)

        params = {
            "from": from_junction["code"],
            "to": to_small["code"],
            "date": date
        }

        res = requests.get(API_URL, headers=headers, params=params, timeout=15)
        data = res.json()
        trains = data.get("trains") or data.get("data", {}).get("trains", [])

        if trains:
            route_mode = "Junction → Small"
            from_station = from_junction
            to_station = to_small

    # STEP 4: JUNCTION → JUNCTION
    if not trains:
        from_junction = find_nearest(from_lat, from_lon, junction_stations)
        to_junction = find_nearest(to_lat, to_lon, junction_stations)

        params = {
            "from": from_junction["code"],
            "to": to_junction["code"],
            "date": date
        }

        res = requests.get(API_URL, headers=headers, params=params, timeout=15)
        data = res.json()
        trains = data.get("trains") or data.get("data", {}).get("trains", [])

        if trains:
            route_mode = "Junction → Junction"
            from_station = from_junction
            to_station = to_junction

    # STEP 5: SOURCE JUNCTION EXPANSION
    if not trains:
        to_junction = find_nearest(to_lat, to_lon, junction_stations)

        source_junctions = nearest_junctions(
            from_lat, from_lon, junction_stations, 10
        )

        for j in source_junctions:
            params = {
                "from": j["code"],
                "to": to_junction["code"],
                "date": date
            }

            res = requests.get(API_URL, headers=headers, params=params, timeout=15)
            data = res.json()
            trains = data.get("trains") or data.get("data", {}).get("trains", [])

            if trains:
                route_mode = "Source Junction Expansion"
                from_station = j
                to_station = to_junction
                break

    # NO TRAINS
    if not trains:
        return from_station, to_station, [], [], "No trains found"

    # RANKING
    df = pd.json_normalize(trains).fillna(0)

    df["bestScore"] = (
        (df.get("avgSpeedKmph", 0) * 2)
        - (df.get("travelTimeMinutes", 0) * 0.01)
        - (df.get("totalHalts", 0) * 5)
        + (df.get("runningDays.allDays", 0) * 10)
    )

    df = df.sort_values("bestScore", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", df.index + 1)

    display_cols = [
        "Rank",
        "trainName",
        "travelTimeMinutes",
        "avgSpeedKmph",
        "totalHalts",
        "distanceKm",
        "bestScore"
    ]

    df = df[display_cols]

    return (
        from_station,
        to_station,
        df.values.tolist(),
        df.columns.tolist(),
        route_mode
    )