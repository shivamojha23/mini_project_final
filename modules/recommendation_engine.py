# modules/recommendation_engine.py

from models import db, History
from datetime import datetime

def get_option_comfort(opt):
    if 'comfort' in opt and opt['comfort'] is not None:
        return float(opt['comfort'])
    
    # Get mode and name/details to determine comfort
    mode = str(opt.get('mode', '')).lower()
    name = str(opt.get('name', opt.get('bus_type', opt.get('operator', '')))).lower()
    
    if 'flight' in mode:
        return 5.0
    elif 'taxi' in mode or 'cab' in mode:
        return 4.0
    elif 'personal' in mode or 'car' in mode:
        return 3.5
    elif 'train' in mode:
        return 3.5
    elif 'bus' in mode:
        if 'sleeper' in name and ('ac' in name or 'a/c' in name or 'volvo' in name):
            return 4.0
        elif 'seater' in name and ('ac' in name or 'a/c' in name or 'volvo' in name):
            return 3.0
        elif 'sleeper' in name:
            return 3.0
        return 2.5
    return 3.0

def get_recommendation(user_id, source, destination, options_list, preferred_mode=None):
    """
    Personalized recommendation engine for SmartTravel.
    
    Parameters:
    - user_id (int): ID of the current logged-in user
    - source (str): Origin place/city
    - destination (str): Destination place/city
    - options_list (list of dict): Available transport options. Each option dict should contain:
        - 'mode': "Personal", "Taxi", "Train", "Bus", or "Flight"
        - 'price': float or int representation of the cost
        - 'duration': float or int duration in minutes
        - 'name': display name of the option
        - 'comfort': (optional) comfort rating 1.0 to 5.0
        - 'details': (optional) additional text description
    - preferred_mode (str, optional): Explicit preferred transport mode select by the user.
    
    Returns:
    - dict: A dictionary containing 'recommended_option', 'bias', and 'explanation'
    """
    if not options_list:
        return None

    # Retrieve user's last 10 searches ordered by created_at
    searches = []
    if user_id:
        searches = History.query.filter_by(user_id=user_id).order_by(History.created_at.desc()).limit(10).all()

    # Count user booking transit mode preference from history
    dominant_historical_mode = None
    if searches:
        mode_counts = {}
        for s in searches:
            if s.selected_mode:
                mode_counts[s.selected_mode] = mode_counts.get(s.selected_mode, 0) + 1
        if mode_counts:
            dominant_historical_mode = max(mode_counts, key=mode_counts.get)

    # Extract metrics for normalization
    prices = [float(opt['price']) for opt in options_list]
    durations = [float(opt['duration']) for opt in options_list]
    comforts = [get_option_comfort(opt) for opt in options_list]

    min_price, max_price = min(prices), max(prices)
    min_duration, max_duration = min(durations), max(durations)
    min_comfort, max_comfort = min(comforts), max(comforts)

    # Normalization helper functions
    # 0.0 is worst (e.g., highest price/duration), 1.0 is best (lowest price/duration)
    def normalize_min_best(val, min_val, max_val):
        if max_val == min_val:
            return 1.0
        return 1.0 - (val - min_val) / (max_val - min_val)

    # 1.0 is best (highest comfort), 0.0 is worst (lowest comfort)
    def normalize_max_best(val, min_val, max_val):
        if max_val == min_val:
            return 1.0
        return (val - min_val) / (max_val - min_val)

    # Determine dominant bias and weighting scheme
    if len(searches) < 3:
        # Cold start fallback: optimal ratio of price-to-duration (Balanced weights, comfort not weighted)
        price_w, dur_w, com_w = 0.5, 0.5, 0.0
        bias_name = "Cold Start (Best Value)"
    else:
        # Count user preferences in history
        pref_counts = {"Cheapest": 0, "Fastest": 0, "Comfortable": 0, "Balanced": 0}
        for s in searches:
            if s.preference in pref_counts:
                pref_counts[s.preference] += 1
            elif s.preference:
                # Map alternate strings
                clean_pref = s.preference.strip()
                if "Cheapest" in clean_pref or "Affordability" in clean_pref:
                    pref_counts["Cheapest"] += 1
                elif "Fastest" in clean_pref or "Speed" in clean_pref:
                    pref_counts["Fastest"] += 1
                elif "Comfortable" in clean_pref or "Comfort" in clean_pref:
                    pref_counts["Comfortable"] += 1
                else:
                    pref_counts["Balanced"] += 1
                    
        # Identify dominant preference
        dominant = max(pref_counts, key=pref_counts.get)
        
        # Set weights based on bias
        if dominant == "Cheapest":
            price_w, dur_w, com_w = 0.7, 0.2, 0.1
            bias_name = "Affordability"
        elif dominant == "Fastest":
            price_w, dur_w, com_w = 0.2, 0.7, 0.1
            bias_name = "Speed"
        elif dominant == "Comfortable":
            price_w, dur_w, com_w = 0.15, 0.15, 0.7
            bias_name = "Comfort"
        else:
            price_w, dur_w, com_w = 0.4, 0.4, 0.2
            bias_name = "Balanced"

    # Score each option
    scored_options = []
    for opt in options_list:
        p_val = float(opt['price'])
        d_val = float(opt['duration'])
        c_val = get_option_comfort(opt)
        opt_mode = opt.get('mode', '')

        p_score = normalize_min_best(p_val, min_price, max_price)
        d_score = normalize_min_best(d_val, min_duration, max_duration)
        c_score = normalize_max_best(c_val, min_comfort, max_comfort)

        # Base score from preferences
        score = (p_score * price_w) + (d_score * dur_w) + (c_score * com_w)
        
        # Mode Preference Boosts
        boost = 0.0
        # Direct preferred mode boost
        if preferred_mode and str(preferred_mode).lower() == opt_mode.lower():
            boost += 0.35
        # Learned historical mode boost
        if dominant_historical_mode and str(dominant_historical_mode).lower() == opt_mode.lower():
            boost += 0.15
            
        score = score + boost
        
        scored_options.append({
            "option": opt,
            "score": score,
            "duration": d_val,
            "price": p_val
        })

    # Sort: highest score first.
    # Tie-breaker: default to option with shortest duration, then lowest price.
    scored_options.sort(key=lambda x: (-x['score'], x['duration'], x['price']))

    best = scored_options[0]['option']
    
    # Generate explanation text
    opt_name = best.get("name", best.get("mode", "Option"))
    opt_mode = best.get("mode", "transport")
    
    if bias_name == "Affordability":
        explanation = f"We recommended the {opt_name} ({opt_mode.lower()}) because it offers a highly budget-friendly cost of ₹{best['price']:,} matching your preference for affordable routes."
    elif bias_name == "Speed":
        explanation = f"We recommended the {opt_name} ({opt_mode.lower()}) to save you time, as it has a short duration of {best['duration']:.1f} mins matching your preference for the fastest routes."
    elif bias_name == "Comfort":
        explanation = f"We recommended the {opt_name} ({opt_mode.lower()}) for premium comfort based on your preference for cozy and comfortable journeys."
    elif bias_name == "Cold Start (Best Value)":
        explanation = f"We recommended the {opt_name} ({opt_mode.lower()}) because it offers the optimal balance of price (₹{best['price']:,}) and travel duration ({best['duration']:.1f} mins)."
    else:
        explanation = f"We recommended the {opt_name} ({opt_mode.lower()}) as it provides the most balanced option across price, speed, and comfort."

    # Append mode preference details to explanation
    if preferred_mode and str(preferred_mode).lower() == opt_mode.lower():
        explanation += f" This transit matches your explicitly preferred mode of travel ({opt_mode})."
    elif dominant_historical_mode and str(dominant_historical_mode).lower() == opt_mode.lower():
        explanation += f" This transit matches your most frequently booked travel mode ({opt_mode}) from your trip history."

    return {
        "recommended_option": best,
        "bias": bias_name,
        "explanation": explanation
    }
