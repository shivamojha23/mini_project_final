from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from route_module import get_route_data, preload_gateway_segments
import folium
import requests
from config.settings import Config
from flight_serpapi import get_flights_serpapi
from utils.flight_helpers import get_lat_lon, find_nearest_airport
from models import db, User, History

# ── Bus & Train module imports ──────────────────────────────
from modules.train_module import (
    get_best_trains,
    load_stations,
    find_nearest,
    get_lat_lon as train_get_lat_lon
)
from modules.bus_service import get_buses

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'shivam_smart_travel_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_travel.db'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from config.constants import (
    GEOAPIFY_KEY, KNOWN_PLACES, MAJOR_CITIES,
    ISLAMPUR, SILIGURI, SILCHAR, PILIBHIT, LUCKNOW, NORTHEAST_STATES
)
from utils.helpers import (
    get_state, in_ne, geocode, is_north_of_siliguri, format_time, fare
)

# Pre-cache fixed gateway segments at startup
preload_gateway_segments()

# Load train station data
small_stations    = load_stations("all_india_stations_small.csv")
junction_stations = load_stations("final_junction1.csv")


# =============================================================
# AUTH — user loader
# =============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =============================================================
# AUTH ROUTES  (verbatim from bus & train module)
# =============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user  = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('login_register.html', mode='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login_register.html', mode='login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# =============================================================
# AUTOCOMPLETE
# =============================================================

@app.route("/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q", "").lower()

    known  = [k.title() for k in KNOWN_PLACES if q in k]
    cities = [c for c in MAJOR_CITIES if q in c.lower()]

    api = []
    try:
        url    = "https://api.geoapify.com/v1/geocode/autocomplete"
        params = {"text": q, "apiKey": GEOAPIFY_KEY, "limit": 5}
        data   = requests.get(url, params=params).json()
        api    = [f["properties"]["formatted"] for f in data.get("features", [])]
    except:
        pass

    return jsonify(list(dict.fromkeys(known + cities + api))[:6])


# =============================================================
# MAIN ROUTE MODULE HOME
# =============================================================

@app.route("/", methods=["GET", "POST"])
@login_required
def home():

    if request.method == "POST":
        source = request.form.get("source")
        dest   = request.form.get("destination")

        s = geocode(source)
        d = geocode(dest)

        s_state = get_state(*s)
        d_state = get_state(*d)

        s_ne = in_ne(*s)
        d_ne = in_ne(*d)

        d_tm = d_state in ["Tripura", "Mizoram"]
        s_tm = s_state in ["Tripura", "Mizoram"]
        s_nm = s_state in ["Nagaland", "Manipur"]
        d_nm = d_state in ["Nagaland", "Manipur"]

        s_uk = (28.7 <= s[0] <= 31.2 and 77.6 <= s[1] <= 81.1)
        d_uk = (28.7 <= d[0] <= 31.2 and 77.6 <= d[1] <= 81.1)

        # ---------- ROUTING LOGIC (unchanged) ----------

        if s_ne and d_ne:
            if s_state == "Assam" and d_tm:
                r1, d1, t1 = get_route_data(s, SILCHAR)
                r2, d2, t2 = get_route_data(SILCHAR, d)
                route = r1 + r2; dist = d1 + d2; dur = t1 + t2
            elif s_tm and d_state == "Assam":
                r1, d1, t1 = get_route_data(s, SILCHAR)
                r2, d2, t2 = get_route_data(SILCHAR, d)
                route = r1 + r2; dist = d1 + d2; dur = t1 + t2
            elif s_nm and d_tm:
                route, dist, dur = get_route_data(s, d)
            elif s_tm and d_nm:
                route, dist, dur = get_route_data(s, d)
            else:
                route, dist, dur = get_route_data(s, d)

        elif s_uk and d_ne:
            r1, d1, t1 = get_route_data(s, PILIBHIT)
            r2, d2, t2 = get_route_data(PILIBHIT, ISLAMPUR)
            r3, d3, t3 = get_route_data(ISLAMPUR, SILIGURI)
            route = r1 + r2 + r3; dist = d1 + d2 + d3; dur = t1 + t2 + t3
            if d_tm:
                r4, d4, t4 = get_route_data(SILIGURI, SILCHAR)
                r5, d5, t5 = get_route_data(SILCHAR, d)
                route += r4 + r5; dist += d4 + d5; dur += t4 + t5
            else:
                r4, d4, t4 = get_route_data(SILIGURI, d)
                route += r4; dist += d4; dur += t4

        elif s_ne and d_uk:
            if s_tm:
                r1, d1, t1 = get_route_data(s, SILCHAR)
                r2, d2, t2 = get_route_data(SILCHAR, SILIGURI)
                route = r1 + r2; dist = d1 + d2; dur = t1 + t2
            else:
                r1, d1, t1 = get_route_data(s, SILIGURI)
                route = r1; dist = d1; dur = t1
            r_a, d_a, t_a = get_route_data(SILIGURI, ISLAMPUR)
            r_b, d_b, t_b = get_route_data(ISLAMPUR, PILIBHIT)
            r_c, d_c, t_c = get_route_data(PILIBHIT, d)
            route += r_a + r_b + r_c; dist += d_a + d_b + d_c; dur += t_a + t_b + t_c

        elif not s_ne and d_ne:
            if is_north_of_siliguri(s[0], s[1]) and s[1] < 85.0:
                r1, d1, t1 = get_route_data(s, LUCKNOW)
                r2, d2, t2 = get_route_data(LUCKNOW, ISLAMPUR)
                r3, d3, t3 = get_route_data(ISLAMPUR, SILIGURI)
                route = r1 + r2 + r3; dist = d1 + d2 + d3; dur = t1 + t2 + t3
            elif is_north_of_siliguri(s[0], s[1]):
                r1, d1, t1 = get_route_data(s, SILIGURI)
                route = r1; dist = d1; dur = t1
            else:
                r1, d1, t1 = get_route_data(s, ISLAMPUR)
                r2, d2, t2 = get_route_data(ISLAMPUR, SILIGURI)
                route = r1 + r2; dist = d1 + d2; dur = t1 + t2
            if d_tm:
                r3, d3, t3 = get_route_data(SILIGURI, SILCHAR)
                r4, d4, t4 = get_route_data(SILCHAR, d)
                route += r3 + r4; dist += d3 + d4; dur += t3 + t4
            else:
                r3, d3, t3 = get_route_data(SILIGURI, d)
                route += r3; dist += d3; dur += t3

        elif s_ne and not d_ne:
            if s_tm:
                r1, d1, t1 = get_route_data(s, SILCHAR)
                r2, d2, t2 = get_route_data(SILCHAR, SILIGURI)
                route = r1 + r2; dist = d1 + d2; dur = t1 + t2
            else:
                r1, d1, t1 = get_route_data(s, SILIGURI)
                route = r1; dist = d1; dur = t1
            if is_north_of_siliguri(d[0], d[1]) and d[1] < 85.0:
                r_a, d_a, t_a = get_route_data(SILIGURI, ISLAMPUR)
                r_b, d_b, t_b = get_route_data(ISLAMPUR, LUCKNOW)
                r_c, d_c, t_c = get_route_data(LUCKNOW, d)
                route += r_a + r_b + r_c; dist += d_a + d_b + d_c; dur += t_a + t_b + t_c
            elif is_north_of_siliguri(d[0], d[1]):
                r_last, d_last, t_last = get_route_data(SILIGURI, d)
                route += r_last; dist += d_last; dur += t_last
            else:
                r_a, d_a, t_a = get_route_data(SILIGURI, ISLAMPUR)
                r_b, d_b, t_b = get_route_data(ISLAMPUR, d)
                route += r_a + r_b; dist += d_a + d_b; dur += t_a + t_b

        else:
            route, dist, dur = get_route_data(s, d)

        # ---------- MAP ----------
        m = folium.Map(location=route[0], zoom_start=6)
        folium.PolyLine(route, color="blue").add_to(m)
        folium.Marker(route[0], popup="Start").add_to(m)
        folium.Marker(route[-1], popup="End").add_to(m)

        return render_template("index.html",
                               map=m._repr_html_(),
                               distance=round(dist, 2),
                               taxi_fare=fare(dist),
                               estimated_time=format_time(dur),
                               has_route=True,
                               source=source,
                               destination=dest,
                               s_lat=s[0], s_lon=s[1],
                               d_lat=d[0], d_lon=d[1],
                               user=current_user)

    # GET: pre-fill source/destination/module from query params (e.g. coming back from plan/bus)
    source = request.args.get("source", "")
    dest   = request.args.get("destination", "")
    module = request.args.get("module", "route")
    return render_template("index.html", has_route=False, user=current_user,
                           source=source, destination=dest, active_module=module)


# =============================================================
# FLIGHT ROUTES  (unchanged)
# =============================================================

@app.route("/flight")
@login_required
def flight_index():
    from_place = request.args.get("from_place", "").strip()
    to_place   = request.args.get("to_place",   "").strip()
    return render_template("flight_index.html", from_place=from_place, to_place=to_place)


@app.route("/flight/results")
@login_required
def flight_results():
    from_place = request.args.get("from_place", "").strip()
    to_place   = request.args.get("to_place",   "").strip()
    date       = request.args.get("date",        "").strip()

    from_lat = request.args.get("from_lat")
    from_lon = request.args.get("from_lon")
    to_lat   = request.args.get("to_lat")
    to_lon   = request.args.get("to_lon")

    if not from_place or not to_place or not date:
        return render_template("error.html", message="Please fill all fields."), 400

    if from_lat and from_lon and to_lat and to_lon:
        from_lat, from_lon = float(from_lat), float(from_lon)
        to_lat,   to_lon   = float(to_lat),   float(to_lon)
    else:
        try:
            from_lat, from_lon = geocode(from_place)
        except:
            from_lat = from_lon = None
        try:
            to_lat, to_lon = geocode(to_place)
        except:
            to_lat = to_lon = None

    if not from_lat or not to_lat:
        return render_template("error.html", message="Could not geocode one or both locations."), 400

    from_airport = find_nearest_airport(from_lat, from_lon)
    to_airport   = find_nearest_airport(to_lat,   to_lon)

    raw_flights  = get_flights_serpapi(from_airport["code"], to_airport["code"], date)

    flights_list = []
    for idx, f in enumerate(raw_flights, start=1):
        price_display = f"₹ {f['price_inr']:,}" if f["price_inr"] > 0 else "Check site"
        flights_list.append({
            "rank":      idx,
            "airline":   f["airline"],
            "flight_no": f["flight_no"],
            "airplane":  f.get("airplane", ""),
            "route":     f["route"],
            "departure": f["departure"],
            "arrival":   f["arrival"],
            "duration":  f["duration"],
            "stops":     "Non-stop" if f["stops"] == 0 else f"{f['stops']} stop(s)",
            "price":     price_display,
            "price_raw": f["price_inr"],
            "carbon_kg": f.get("carbon_kg", 0),
        })

    return render_template(
        "results.html",
        flights=flights_list,
        from_place=from_place,
        to_place=to_place,
        from_airport=from_airport,
        to_airport=to_airport,
        date=date,
        total=len(flights_list),
        from_lat=from_lat,
        from_lon=from_lon,
        to_lat=to_lat,
        to_lon=to_lon,
    )


# =============================================================
# BUS & TRAIN PLAN ROUTES  (verbatim logic from bus & train module)
# =============================================================

def plan_journey(from_place, to_place, date):
    routes = []

    from_station, to_station, trains, cols, mode = get_best_trains(
        from_place, to_place, date, small_stations, junction_stations
    )

    if not trains:
        return []

    _, _, first_leg_trains, _, _ = get_best_trains(
        from_place, from_station["name"], date, small_stations, junction_stations
    )

    # ROUTE 1: TRAIN + TRAIN
    if first_leg_trains:
        route = []
        step  = 1
        route.append({"step": step, "mode": "TRAIN", "from": from_place,
                      "to": from_station["name"], "data": first_leg_trains[:3]})
        step += 1
        route.append({"step": step, "mode": "TRAIN", "from": from_station["name"],
                      "to": to_station["name"], "data": trains[:3]})
        step += 1
        if to_place.lower() != to_station["name"].lower():
            _, _, last_leg_trains, _, _ = get_best_trains(
                to_station["name"], to_place, date, small_stations, junction_stations
            )
            if last_leg_trains:
                route.append({"step": step, "mode": "TRAIN", "from": to_station["name"],
                              "to": to_place, "data": last_leg_trains[:3]})
        routes.append({"route_id": 1, "type": "Train + Train", "steps": route})

    # ROUTE 2: BUS + TRAIN
    route = []
    step  = 1
    if from_place.lower() != from_station["name"].lower():
        bus1 = get_buses(from_place, from_station["name"], date)
        if not bus1:
            bus1 = [{"msg": "Take local transport", "price": "₹100-₹300"}]
        route.append({"step": step, "mode": "BUS", "from": from_place,
                      "to": from_station["name"], "data": bus1})
        step += 1
    route.append({"step": step, "mode": "TRAIN", "from": from_station["name"],
                  "to": to_station["name"], "data": trains[:3]})
    step += 1
    if to_place.lower() != to_station["name"].lower():
        bus2 = get_buses(to_station["name"], to_place, date,
                         dist_km=to_station.get("distance_km", 0))
        if not bus2:
            bus2 = [{"msg": "Take local transport", "price": "₹80-₹200"}]
        route.append({"step": step, "mode": "BUS", "from": to_station["name"],
                      "to": to_place, "data": bus2})
    routes.append({"route_id": len(routes) + 1, "type": "Bus + Train", "steps": route})

    # RANKING
    for r in routes:
        r["score"] = calculate_route_score(r)
    routes = sorted(routes, key=lambda x: x["score"])
    if routes:
        routes[0]["best"] = True

    return routes


def calculate_route_score(route):
    total_time = 0
    total_price = 0
    bus_penalty = 0
    for step in route["steps"]:
        for item in step["data"]:
            if step["mode"] == "TRAIN":
                try:
                    total_time  += int(item[2])
                    total_price += 200
                except:
                    pass
            elif step["mode"] == "BUS":
                try:
                    total_time  += float(item.get("duration", 2)) * 60
                    total_price += int(str(item.get("price", "100")).replace("₹", "").split("-")[0])
                    bus_penalty += 50
                except:
                    pass
    return total_time + total_price + bus_penalty


def lookup_station_coords(name_or_code):
    """Look up lat/lon from loaded station lists by name or code."""
    for s in small_stations + junction_stations:
        if s["name"].lower() == name_or_code.lower() or s["code"].lower() == name_or_code.lower():
            return s["lat"], s["lon"]
    return None, None


@app.route("/plan/json")
@login_required
def plan_json():
    """JSON endpoint — returns train routes for inline AJAX loading in index.html"""
    source      = request.args.get("source", "")
    destination = request.args.get("destination", "")
    date        = request.args.get("date", "")
    try:
        routes = plan_journey(source, destination, date)
    except Exception as e:
        print(f"[PLAN JSON ERROR] {e}")
        routes = []

    try:
        from_lat, from_lon = geocode(source)
    except:
        from_lat = from_lon = None
    try:
        to_lat, to_lon = geocode(destination)
    except:
        to_lat = to_lon = None

    from_stn_lat = from_stn_lon = to_stn_lat = to_stn_lon = None
    from_stn_name = to_stn_name = ""
    if routes:
        for step in routes[0]["steps"]:
            if step["mode"] == "TRAIN":
                sla, slo = lookup_station_coords(step["from"])
                dla, dlo = lookup_station_coords(step["to"])
                if sla and dla:
                    from_stn_lat, from_stn_lon = sla, slo
                    to_stn_lat, to_stn_lon = dla, dlo
                    from_stn_name = step["from"]
                    to_stn_name = step["to"]
                    break

    return jsonify({
        "routes": routes,
        "from_lat": from_lat, "from_lon": from_lon,
        "to_lat": to_lat, "to_lon": to_lon,
        "from_stn_lat": from_stn_lat, "from_stn_lon": from_stn_lon,
        "to_stn_lat": to_stn_lat, "to_stn_lon": to_stn_lon,
        "from_stn_name": from_stn_name, "to_stn_name": to_stn_name,
    })


@app.route("/bus/json")
@login_required
def bus_json():
    """JSON endpoint — returns bus results for inline AJAX loading in index.html"""
    source      = request.args.get("source", "")
    destination = request.args.get("destination", "")
    date        = request.args.get("date", "")

    try:
        from_lat, from_lon = geocode(source)
    except:
        from_lat = from_lon = None
    try:
        to_lat, to_lon = geocode(destination)
    except:
        to_lat = to_lon = None

    buses = get_buses(source, destination, date) or []

    return jsonify({
        "buses": buses,
        "from_lat": from_lat, "from_lon": from_lon,
        "to_lat": to_lat, "to_lon": to_lon,
    })


@app.route("/plan")
@login_required
def plan():
    source      = request.args.get("source")
    destination = request.args.get("destination")
    date        = request.args.get("date")
    try:
        routes = plan_journey(source, destination, date)
    except Exception as e:
        print(f"[PLAN ERROR] {e}")
        routes = []

    # Geocode user source/destination
    try:
        from_lat, from_lon = geocode(source)
    except:
        from_lat = from_lon = None
    try:
        to_lat, to_lon = geocode(destination)
    except:
        to_lat = to_lon = None

    # Look up station coordinates from the first route's main train leg
    from_stn_lat = from_stn_lon = to_stn_lat = to_stn_lon = None
    from_stn_name = to_stn_name = ""
    if routes:
        for step in routes[0]["steps"]:
            if step["mode"] == "TRAIN":
                sla, slo = lookup_station_coords(step["from"])
                dla, dlo = lookup_station_coords(step["to"])
                if sla and dla:
                    from_stn_lat, from_stn_lon = sla, slo
                    to_stn_lat, to_stn_lon = dla, dlo
                    from_stn_name = step["from"]
                    to_stn_name = step["to"]
                    break

    return render_template("plan.html",
        source=source, destination=destination, routes=routes,
        from_lat=from_lat, from_lon=from_lon,
        to_lat=to_lat, to_lon=to_lon,
        from_stn_lat=from_stn_lat, from_stn_lon=from_stn_lon,
        to_stn_lat=to_stn_lat, to_stn_lon=to_stn_lon,
        from_stn_name=from_stn_name, to_stn_name=to_stn_name,
        date=date,
    )


# =============================================================
# BUS MODULE  (separate from plan — dedicated bus search with map)
# =============================================================

@app.route("/bus")
@login_required
def bus():
    source      = request.args.get("source")
    destination = request.args.get("destination")
    date        = request.args.get("date", "")

    if not source or not destination:
        return render_template("bus.html", source=source or "", destination=destination or "",
                               buses=[], from_lat=None, from_lon=None, to_lat=None, to_lon=None, date=date)

    # Geocode
    try:
        from_lat, from_lon = geocode(source)
    except:
        from_lat = from_lon = None
    try:
        to_lat, to_lon = geocode(destination)
    except:
        to_lat = to_lon = None

    # Get buses
    buses = get_buses(source, destination, date) or []

    return render_template("bus.html",
        source=source, destination=destination,
        buses=buses, date=date,
        from_lat=from_lat, from_lon=from_lon,
        to_lat=to_lat, to_lon=to_lon,
    )


# =============================================================
# RUN
# =============================================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)