# ✈️ SmartTravel - Indian Multi-Modal Journey Planner & Personalized Recommender

Welcome to **SmartTravel**, a premium, high-tech, multi-modal travel routing, corridor connectivity planner, and personalized booking dashboard tailored specifically for intercity transit across India. 

SmartTravel unifies distinct Indian transport sectors—including Train networks (via local station and junction coordinates), live Bus routes (with national RTC & premium private operators), Flight corridors (using SerpAPI Google Flights), Taxis/Cabs, and Personal Vehicles—into a cohesive, dark-themed, glassmorphic dashboard interface.

---

## 🌟 Key Features

### 🗺️ 1. Geospatial Dark-Mode Maps
- Interactive map canvases powered by **Folium** and **Leaflet.js**.
- Embedded **OSRM road routing engines** calculating accurate highway mileage and times.
- Premium dark-theme custom Leaflet tile filters rendering neon network arcs for flight vectors, train corridors, and taxi driving tracks.
- Hover-interactive route checkpoints and leg-by-leg timeline summary cards.

### 🚆 2. Indian Railway corridor connects
- Automatic coordinates mapping via a small Indian railway stations dataset and junction dataset.
- Dynamic route segment planning including multi-modal fallback connections (e.g. **Bus + Train** connections).
- IRCTC click tracking to capture passenger booking intent.

### 🚌 3. Scrapers & RTC Operators dataset
- Interactive bus corridors preloading a diverse synthetic dataset of **25 unique intercity routes** spanning North, South, Central, and Western India.
- Supports major **State RTCs** (MSRTC, GSRTC, KSRTC, UPSRTC), **Premium Private Operators** (VRL, Hans, Chartered), and **Modern Electric Operators** (NueGo, FreshBus).
- Live **Selenium RedBus scraper** parsing departures and prices dynamically.
- Distance-based fallback pricing ranges if scraping is blocked or returning empty fares.

### ✈️ 4. Google Flights serpapi integration
- Active connection to **SerpAPI Google Flights** fetching actual domestic fares in INR.
- Free-tier saving cache that saves search dates and routes locally for **6 hours** to avoid wasting API quota.
- Automatic **Haversine distance-based fallback pricing** (e.g. `₹4,500 - ₹6,250`) to guarantee correct display even when offline.

### 🧠 5. MCDA Personalized Recommendation engine
- Multi-Criteria Decision Analysis (MCDA) that normalizes prices, speed, and comfort indices into a unified mathematical plane.
- Dynamic weight profiles adjusted to user preferences (Fastest, Cheapest, Comfortable, Balanced).
- **Direct Mode Boost (+0.35)**: Applies a score boost if a route matches the user's explicitly selected preferred transport mode.
- **Historical Booked Boost (+0.15)**: Automatically computes your most frequently booked transit mode and applies an incremental boost.
- Generates beautiful, explainable recommendation text cards detailing why the choice was selected.

### 📊 6. Post-Search Surveys
- A glassmorphic survey block asking *"Which transit mode do you generally prefer for this route?"*.
- Clicking a button fires an **asynchronous AJAX POST** to record selections, smoothly fades the card, and fires a neon success toast.

---

## 📂 Codebase Directory Structure

```text
SmartTravel/
│
├── app.py                     # Main Flask entrypoint & API routes
├── models.py                  # Database tables (User, History)
├── route_module.py            # OSRM routing interface & gateway pre-caching
├── flight_serpapi.py          # Google Flights SerpAPI fetcher & Cache
├── location_module.py         # Geoapify place geocoder & autocomplete
│
├── config/
│   ├── constants.py           # Northeast coordinates boundary parameters
│   └── settings.py            # Third-party tokens & secret keys
│
├── modules/
│   ├── recommendation_engine.py  # Normalization, weight biases, & boost scoring
│   ├── bus_service.py         # Bus schedules and fallback price ranges
│   ├── bus_scraper.py         # Selenium RedBus parser (Undetected ChromeDriver)
│   └── train_module.py        # Railway connect calculations & junctions
│
├── utils/
│   ├── helpers.py             # Geocoding wrappers & Northeast boundary logic
│   └── flight_helpers.py      # Airport CSV loader & Haversine formula
│
├── templates/
│   ├── index.html             # Main dashboard, search form, and survey card
│   ├── plan.html              # Dedicated train connect corridors and arcs
│   ├── bus.html               # Dedicated bus schedules list and map
│   ├── results.html           # Dedicated flight results and airport markers
│   ├── login_register.html    # Authentication view (Login / Register)
│   └── error.html             # Safe fallback error page
│
├── scratch/
│   ├── test_preferences.py    # Standalone recommendation boosts test suite
│   ├── test_database.py       # Standalone SQLite database integrity tests
│   └── test_templates.py      # Standalone Flask views rendering checks
│
├── rebuild_project.py         # Unified, self-extracting project rebuilder
├── AI_SYSTEM_SPEC.md          # Architectural guide optimized for AI agents
└── README.md                  # Human developer onboarding guide (This file)
```

---

## ⚡ Quick Start & Installation

Ensure you have **Python 3.8+** installed. 

### 1. Initialize Virtual Environment:
```bash
# Clone the repository and enter the directory
cd route_module

# Create virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Package Dependencies:
```bash
pip install flask flask-sqlalchemy flask-login flask-migrate folium requests pandas pyarrow fastparquet geopy selenium undetected-chromedriver
```

### 3. Run Database Migrations:
SmartTravel uses Flask-Migrate (Alembic) to version schema changes without purging data.
```bash
flask db init
flask db migrate -m "Initialize travel database"
flask db upgrade
```

### 4. Paste API Keys (Optional but recommended):
Open `flight_serpapi.py` and configure your **SerpAPI key** to enable actual Google Flights indexing:
```python
SERPAPI_KEY = "your_free_serpapi_key"
```

### 5. Launch the Application:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000/`. Create an account, log in, and start planning routes!

---

## 🧪 Run Verification Test Suites

SmartTravel contains modular, non-intrusive tests that check logic, databases, and UI renders without needing active browser testing:

```bash
# Test direct preferred boosts and historical booking logic
python scratch/test_preferences.py

# Test SQLite columns integrity and affordability/speed weight biases
python scratch/test_database.py

# Test Flask template engines rendering pages successfully
python scratch/test_templates.py
```

---

## 📦 System Rebuilder & AI Spec Sheets
- If you need to replicate this application in a clean workspace folder, simply copy `rebuild_project.py` and run `python rebuild_project.py` to automatically unpack the entire codebase.
- Review `AI_SYSTEM_SPEC.md` for a comprehensive, mathematical model of the recommendation formulas, scoring matrices, and database tables.
