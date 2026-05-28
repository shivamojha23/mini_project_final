def get_road_trip(dist_km):
    time = round(dist_km / 50, 1)
    cost_low, cost_high = int(dist_km * 10), int(dist_km * 15)
    return [{
        "type": "Car/Taxi", "operator": "Uber Intercity / Private Cab", "bus_type": "Direct Road",
        "depart": "Anytime", "duration": time, "price": f"{cost_low} - {cost_high}", 
        "rating": "4.8", "punctuality": 100, "icon": "🚗", "link": "https://www.uber.com/in/en/"
    }]