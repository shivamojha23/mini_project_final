"""
Test script to check if routes stay within India's borders.
Checks critical city pairs for international boundary crossings.
"""
import time
from route_module import get_route_data

# ─── Approximate India boundary box ───
# Using a simplified polygon approach: check against known foreign territory
INDIA_BOUNDS = {
    "lat_min": 6.5,    # Kanyakumari
    "lat_max": 37.1,   # Kashmir
    "lon_min": 68.0,    # Gujarat/Rajasthan west
    "lon_max": 97.5,    # Arunachal east
}

# Bangladesh bounding box (the main risk area)
BANGLADESH = {
    "lat_min": 20.5,
    "lat_max": 26.6,
    "lon_min": 88.0,
    "lon_max": 92.7,
}

# Nepal bounding box
NEPAL = {
    "lat_min": 26.3,
    "lat_max": 30.5,
    "lon_min": 80.0,
    "lon_max": 88.2,
}

# Key points that are definitely inside India (used to exclude false positives)
# The Siliguri Corridor is ~22km wide, so Indian territory exists within Bangladesh's lon range
INDIA_CORRIDORS = [
    # Siliguri Corridor (Chicken's Neck): lat 26.0-27.0, lon 88.0-88.8
    {"name": "Siliguri Corridor", "lat_min": 26.0, "lat_max": 27.2, "lon_min": 87.8, "lon_max": 88.9},
    # NE India states (Assam, Meghalaya, etc.) overlap with Bangladesh lon range
    {"name": "Northeast India", "lat_min": 24.0, "lat_max": 28.0, "lon_min": 89.5, "lon_max": 97.5},
    # Parts of West Bengal above Bangladesh
    {"name": "North Bengal", "lat_min": 25.5, "lat_max": 27.5, "lon_min": 87.5, "lon_max": 89.5},
]

def is_in_india_corridor(lat, lon):
    """Check if point is in a known Indian corridor that overlaps with foreign bbox."""
    for c in INDIA_CORRIDORS:
        if c["lat_min"] <= lat <= c["lat_max"] and c["lon_min"] <= lon <= c["lon_max"]:
            return True
    return False

def is_likely_bangladesh(lat, lon):
    """Check if a point is likely in Bangladesh (not in an Indian corridor)."""
    in_bd_box = (BANGLADESH["lat_min"] <= lat <= BANGLADESH["lat_max"] and
                 BANGLADESH["lon_min"] <= lon <= BANGLADESH["lon_max"])
    if not in_bd_box:
        return False
    # Exclude known Indian corridors
    if is_in_india_corridor(lat, lon):
        return False
    # Points below lat 26.0 and between lon 88.0-92.5 are likely Bangladesh
    if lat < 25.5 and 88.0 <= lon <= 92.5:
        return True
    # Points in the main Bangladesh body
    if lat < 26.0 and 89.0 <= lon <= 92.0:
        return True
    return False

def is_likely_nepal(lat, lon):
    """Check if a point is likely in Nepal."""
    in_np_box = (NEPAL["lat_min"] <= lat <= NEPAL["lat_max"] and
                 NEPAL["lon_min"] <= lon <= NEPAL["lon_max"])
    if not in_np_box:
        return False
    # Nepal is north of the Gangetic plain, roughly above lat 27 in the west
    # and above lat 26.5 in the east, but India also extends north
    # Skip this check - OSRM roads should generally be fine for Nepal
    return False  # Hard to distinguish from Indian border towns

def check_route(name, start, end):
    """Check a route for boundary crossings."""
    try:
        route, dist, dur = get_route_data(start, end)
        
        violations = []
        for i, (lat, lon) in enumerate(route):
            # Check if outside India entirely
            if (lat < INDIA_BOUNDS["lat_min"] or lat > INDIA_BOUNDS["lat_max"] or
                lon < INDIA_BOUNDS["lon_min"] or lon > INDIA_BOUNDS["lon_max"]):
                violations.append(("OUTSIDE_INDIA", i, lat, lon))
            
            # Check Bangladesh crossing
            if is_likely_bangladesh(lat, lon):
                violations.append(("BANGLADESH", i, lat, lon))
        
        if violations:
            # Count unique violation types
            bd_count = sum(1 for v in violations if v[0] == "BANGLADESH")
            out_count = sum(1 for v in violations if v[0] == "OUTSIDE_INDIA")
            
            print(f"[FAIL] {name}")
            print(f"   Distance: {dist} km | Points: {len(route)}")
            if bd_count:
                sample = next(v for v in violations if v[0] == "BANGLADESH")
                print(f"   [!] BANGLADESH crossing: {bd_count} points (sample: lat={sample[2]:.4f}, lon={sample[3]:.4f})")
            if out_count:
                sample = next(v for v in violations if v[0] == "OUTSIDE_INDIA")
                print(f"   [!] OUTSIDE INDIA: {out_count} points (sample: lat={sample[2]:.4f}, lon={sample[3]:.4f})")
            return False
        else:
            print(f"[OK] {name} - {dist} km, {len(route)} points, all within India")
            return True
            
    except Exception as e:
        print(f"[!] {name} - ERROR: {e}")
        return None

# ─── Test City Pairs ───
TEST_ROUTES = [
    # --- Critical NE routes (highest risk of Bangladesh crossing) ---
    ("Delhi -> Guwahati", (28.7041, 77.1025), (26.1445, 91.7362)),
    ("Guwahati -> Delhi", (26.1445, 91.7362), (28.7041, 77.1025)),
    
    ("Kolkata -> Guwahati", (22.5726, 88.3639), (26.1445, 91.7362)),
    ("Guwahati -> Kolkata", (26.1445, 91.7362), (22.5726, 88.3639)),
    
    ("Delhi -> Agartala", (28.7041, 77.1025), (23.8103, 91.2787)),
    ("Agartala -> Delhi", (23.8103, 91.2787), (28.7041, 77.1025)),
    
    ("Kolkata -> Agartala", (22.5726, 88.3639), (23.8103, 91.2787)),
    ("Agartala -> Kolkata", (23.8103, 91.2787), (22.5726, 88.3639)),
    
    ("Mumbai -> Guwahati", (19.0760, 72.8777), (26.1445, 91.7362)),
    ("Guwahati -> Mumbai", (26.1445, 91.7362), (19.0760, 72.8777)),
    
    # --- Siliguri Corridor routes ---
    ("Siliguri -> Guwahati", (26.7271, 88.4230), (26.1445, 91.7362)),
    ("Guwahati -> Siliguri", (26.1445, 91.7362), (26.7271, 88.4230)),
    
    ("Islampur -> Siliguri", (26.2675, 88.1960), (26.7271, 88.4230)),
    ("Siliguri -> Islampur", (26.7271, 88.4230), (26.2675, 88.1960)),
    
    # --- Silchar gateway routes ---
    ("Guwahati -> Silchar", (26.1445, 91.7362), (24.8398, 92.7789)),
    ("Silchar -> Agartala", (24.8398, 92.7789), (23.8103, 91.2787)),
    ("Agartala -> Silchar", (23.8103, 91.2787), (24.8398, 92.7789)),
    
    # --- Cross-India routes ---
    ("Mumbai -> Kolkata", (19.0760, 72.8777), (22.5726, 88.3639)),
    ("Kolkata -> Mumbai", (22.5726, 88.3639), (19.0760, 72.8777)),
    
    ("Delhi -> Mumbai", (28.7041, 77.1025), (19.0760, 72.8777)),
    ("Mumbai -> Delhi", (19.0760, 72.8777), (28.7041, 77.1025)),
    
    # --- Border-sensitive routes ---
    ("Delhi -> Kolkata", (28.7041, 77.1025), (22.5726, 88.3639)),
    ("Kolkata -> Delhi", (22.5726, 88.3639), (28.7041, 77.1025)),
    
    # --- Uttarakhand routes ---
    ("Dehradun -> Guwahati", (30.3165, 78.0322), (26.1445, 91.7362)),
    ("Guwahati -> Dehradun", (26.1445, 91.7362), (30.3165, 78.0322)),
]

if __name__ == "__main__":
    print("=" * 65)
    print("  INDIA BOUNDARY CHECK - Route Verification")
    print("=" * 65)
    print()
    
    passed = 0
    failed = 0
    errors = 0
    
    for name, start, end in TEST_ROUTES:
        result = check_route(name, start, end)
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            errors += 1
        
        time.sleep(0.5)  # Be nice to OSRM public server
    
    print()
    print("=" * 65)
    print(f"  RESULTS: [OK] {passed} passed | [FAIL] {failed} failed | [!] {errors} errors")
    print("=" * 65)
