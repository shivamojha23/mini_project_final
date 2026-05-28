# bus_service.py

import pandas as pd
import os
from .bus_scraper import scrape_redbus

try:
    from utils.helpers import geocode
    from route_module import get_route_data
except ImportError:
    geocode = None
    get_route_data = None

CACHE_FILE = "bus_data.parquet"


def get_buses(source, dest, date, dist_km=0):

    # If distance is not provided, try to calculate it dynamically
    if dist_km <= 0:
        if geocode and get_route_data:
            try:
                s_coords = geocode(source)
                d_coords = geocode(dest)
                if s_coords and d_coords:
                    _, dist_km, _ = get_route_data(s_coords, d_coords)
            except Exception as e:
                print(f"[Bus Service Warning] Could not calculate distance for dynamic fallback: {e}")

    # ==============================
    # DATASET SEARCH
    # ==============================
    dataset_buses = _check_dataset(source, dest, date)
    if dataset_buses:
        return dataset_buses

    # ==============================
    # HARDCODED ROUTE (FAST RESPONSE)
    # ==============================
    if source == "Indore" and dest == "Bhopal":
        return [{
            "type": "Bus",
            "operator": "Chartered Bus (Premium)",
            "bus_type": "Volvo A/C Seater",
            "depart": "06:00",
            "duration": "3.5",
            "price": "460",
            "rating": "4.8",
            "punctuality": 99,
            "icon": "🚌",
            "link": "https://www.charteredbus.in/"
        }]

    # ==============================
    # CACHE CHECK
    # ==============================
    cached_data = _check_cache(source, dest, date)
    if cached_data:
        return cached_data

    # ==============================
    # LIVE SCRAPING
    # ==============================
    live_data = scrape_redbus(source, dest, date)

    if live_data:
        enriched_data = _enrich_data(live_data, source, dest, date)
        _update_cache(enriched_data)
        return enriched_data

    # ==============================
    # FALLBACK ESTIMATION
    # ==============================
    return _fallback_estimate(source, dest, dist_km)


# ==================================================
# INTERNAL HELPERS (PRIVATE FUNCTIONS)
# ==================================================

def _check_dataset(source, dest, date):
    dataset_file = "bus_schedules.csv"
    if not os.path.exists(dataset_file):
        return None
    try:
        s_clean = source.split(',')[0].strip().lower()
        d_clean = dest.split(',')[0].strip().lower()
        
        df = pd.read_csv(dataset_file)
        matching = df[
            (df["source"].str.lower() == s_clean) &
            (df["destination"].str.lower() == d_clean)
        ]
        if not matching.empty:
            records = matching.to_dict("records")
            for r in records:
                r["date"] = date
                r["link"] = f"https://www.redbus.in/bus-tickets/{s_clean}-to-{d_clean}?date={date}"
            return records
    except Exception as e:
        print(f"[Bus Service Warning] Dataset check failed: {e}")
    return None


def _check_cache(source, dest, date):

    if not os.path.exists(CACHE_FILE):
        return None

    try:
        df = pd.read_parquet(CACHE_FILE)

        cached = df[
            (df["source"] == source) &
            (df["destination"] == dest) &
            (df["date"] == date)
        ]

        if not cached.empty:
            return cached.to_dict("records")

    except:
        pass

    return None


def _update_cache(new_data):

    new_df = pd.DataFrame(new_data)

    if os.path.exists(CACHE_FILE):
        try:
            existing_df = pd.read_parquet(CACHE_FILE)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_parquet(CACHE_FILE, index=False)
        except:
            new_df.to_parquet(CACHE_FILE, index=False)
    else:
        new_df.to_parquet(CACHE_FILE, index=False)


def _enrich_data(data, source, dest, date):

    for item in data:
        item["source"] = source
        item["destination"] = dest
        item["date"] = date
        item["type"] = "Bus"
        item["icon"] = "🚌"
        item["link"] = f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"

    return data


def _fallback_estimate(source, dest, dist_km):

    if dist_km <= 0:
        dist_km = 200

    est_duration = round(dist_km / 55, 1)
    base_price = int(dist_km * 1.5)

    return [
        {
            "type": "Bus",
            "operator": "Chartered Bus (Premium)",
            "bus_type": "Volvo Multi-Axle A/C Sleeper (2+1)",
            "depart": "07:30",
            "duration": str(round(dist_km / 60, 1)),
            "price": str(int(base_price * 1.4)),
            "rating": "4.7",
            "punctuality": 90,
            "icon": "🚌",
            "link": f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"
        },
        {
            "type": "Bus",
            "operator": "Hans Travels",
            "bus_type": "Bharat Benz A/C Sleeper (2+1)",
            "depart": "12:15",
            "duration": str(round(dist_km / 50, 1)),
            "price": str(int(base_price * 1.1)),
            "rating": "4.2",
            "punctuality": 80,
            "icon": "🚌",
            "link": f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"
        },
        {
            "type": "Bus",
            "operator": "Verma Travels",
            "bus_type": "A/C Seater / Sleeper (2+2)",
            "depart": "18:45",
            "duration": str(round(dist_km / 55, 1)),
            "price": str(int(base_price * 0.9)),
            "rating": "4.0",
            "punctuality": 75,
            "icon": "🚌",
            "link": f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"
        },
        {
            "type": "Bus",
            "operator": "Intercity SmartBus",
            "bus_type": "Premium A/C Sleeper (2+1)",
            "depart": "22:30",
            "duration": str(round(dist_km / 58, 1)),
            "price": str(int(base_price * 1.3)),
            "rating": "4.5",
            "punctuality": 85,
            "icon": "🚌",
            "link": f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"
        }
    ]