"""
ai_engine.py
------------
Rule-based "AI reasoning" layer that turns raw simulated vehicle state
into human-readable insights: cross-system recommendations, an
explainable-AI style breakdown of the overall vehicle score, and a
templated Q&A assistant. This is deliberately transparent logic (if/else
rules over thresholds) rather than a black-box model, matching the
project's "Explainable AI" requirement and keeping everything offline.
"""

import random
from datetime import datetime


def overall_vehicle_score(state: dict) -> dict:
    """
    Combines every subsystem's health into one overall score, plus an AI
    confidence, a risk score, and an efficiency score for the top summary
    card.
    """
    b = state["battery"]["health_percent"]
    m = state["motor"]["health_pct"]
    br = 100 - state["brakes"]["pad_wear_pct"]
    sus = state["suspension"]["shock_health_pct"]
    tires = 100 - (sum(state["tires"]["wear_pct"]) / 4)

    overall = round((b * 0.3 + m * 0.25 + br * 0.15 + sus * 0.15 + tires * 0.15), 1)

    if overall >= 90:
        label = "Excellent"
    elif overall >= 75:
        label = "Good"
    elif overall >= 60:
        label = "Fair"
    else:
        label = "Needs Attention"

    risk_score = round(clamp_val(100 - overall + random.uniform(-3, 3)), 1)
    efficiency_score = round(clamp_val((state["battery"]["charging_efficiency"] +
                                         state["motor"]["efficiency_pct"]) / 2), 1)
    confidence = round(clamp_val(94 + random.uniform(-3, 3)), 1)

    return {
        "overall": overall,
        "label": label,
        "risk_score": risk_score,
        "efficiency_score": efficiency_score,
        "confidence": confidence,
    }


def clamp_val(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def explain_overall_score(state: dict, score_info: dict) -> list:
    """
    Produces an Explainable-AI style breakdown of WHY the overall score is
    what it is, citing the specific subsystems and simulated confidence.
    """
    lines = []
    b = state["battery"]
    m = state["motor"]
    br = state["brakes"]

    lines.append(f"Overall vehicle health is {score_info['overall']}% ({score_info['label']}), confidence {score_info['confidence']}%.")

    if b["factors"] and b["factors"][0] != "No significant risk factors detected":
        lines.append("Battery health decreased because of: " + ", ".join(f.lower() for f in b["factors"]) + ".")
    else:
        lines.append("Battery is performing within its expected healthy range.")

    if m["health_pct"] < 85:
        lines.append(f"Motor health is reduced due to elevated operating temperature ({m['temperature_c']}°C) and vibration levels ({m['vibration_mm_s']} mm/s).")

    if br["pad_wear_pct"] > 40:
        lines.append(f"Brake pad wear is at {br['pad_wear_pct']}%, contributing to a lower mechanical health estimate.")

    return lines


def generate_recommendations(state: dict) -> list:
    """
    Generates cross-system, quantified-sounding AI recommendations by
    scanning driver behaviour, battery, and brake data — the flagship
    "AI Recommendations" feature.
    """
    recs = []
    d = state["driver"]
    b = state["battery"]
    br = state["brakes"]

    if d["acceleration_aggressiveness"] > 60:
        impact = round(5 + (d["acceleration_aggressiveness"] - 60) * 0.15, 1)
        recs.append(f"Reduce hard acceleration to improve battery lifespan by approximately {impact}%.")

    if d["braking_style"] > 55:
        impact = round(10 + (d["braking_style"] - 55) * 0.2, 1)
        recs.append(f"Frequent hard braking increases brake wear by approximately {impact}%.")

    if br["regen_efficiency_pct"] < 75:
        gain = round(75 - br["regen_efficiency_pct"], 1)
        recs.append(f"Using regenerative braking more often could recover approximately {gain}% additional energy.")

    if state["environment"]["temperature_c"] > 35:
        recs.append("Avoid parking in direct sun or high-temperature areas to reduce battery thermal stress.")

    if state["daily"]["avg_speed_kmh"] > 45 and state["daily"]["city_pct"] < 60:
        recs.append("Reduce sustained highway speeds slightly to increase overall driving range.")

    if b["battery_age_months"] > 18 and b["stress_index"] > 40:
        recs.append("Battery calibration recommended this month to maintain accurate SoC readings.")

    if state["motor"]["vibration_mm_s"] > 2.5:
        recs.append("Motor inspection recommended after approximately 2,000 km due to rising vibration levels.")

    if not recs:
        recs.append("All systems operating within optimal parameters. No immediate action needed.")

    return recs


def assistant_answer(question: str, state: dict, score_info: dict) -> str:
    """
    Extremely lightweight templated Q&A "assistant" — matches simple
    keyword patterns in the question to a relevant, data-backed answer
    pulled directly from the current simulated vehicle state. This is
    simulated reasoning, not a real LLM, but is fully offline and
    deterministic given the same state.
    """
    q = question.lower()
    b, m, br, d = state["battery"], state["motor"], state["brakes"], state["driver"]

    if "how is my vehicle" in q or "vehicle health" in q or "overall" in q:
        return (f"Your vehicle is currently rated {score_info['label']} at {score_info['overall']}% overall health. "
                f"Battery is at {b['health_percent']}% ({b['status']}), motor health is {m['health_pct']}%, "
                f"and brake pads show {br['pad_wear_pct']}% wear.")

    if "brake" in q:
        return (f"Brake pad wear is currently {br['pad_wear_pct']}%, with an estimated service distance of "
                f"{br['service_distance_km']} km remaining. Regenerative braking efficiency is {br['regen_efficiency_pct']}%. "
                + ("I'd recommend scheduling a brake inspection soon." if br["pad_wear_pct"] > 50 else "No urgent action needed yet."))

    if "battery life" in q or "increase battery" in q or "battery health" in q:
        tips = "; ".join(b["recommendations"]) if b["recommendations"] else "keep charging between 20-80% and avoid frequent fast charging"
        return f"To extend battery life: {tips}."

    if "efficiency" in q:
        return (f"Current efficiency score is {score_info['efficiency_score']}%. This is influenced by charging efficiency "
                f"({b['charging_efficiency']}%), motor efficiency ({m['efficiency_pct']}%), and driving style "
                f"(eco score: {d['eco_score']}%). Aggressive acceleration and high-speed highway driving tend to reduce it.")

    if "service" in q or "maintenance" in q:
        return "Check the Predictive Maintenance tab for component-by-component service dates, priority levels, and cost estimates."

    if "tire" in q or "tyre" in q:
        avg_wear = round(sum(state["tires"]["wear_pct"]) / 4, 1)
        return f"Average tire wear is {avg_wear}%. Rotation is recommended in {state['tires']['rotation_due_km']} km."

    return ("I can answer questions about battery health, brakes, efficiency, maintenance, or overall vehicle status — "
            "try asking one of those, or use the sample questions above.")


# =======================================================================
# Driver-Friendly Explanation Engine
# -----------------------------------------------------------------------
# Every technical metric in the platform has a full engineering version
# (shown in Insights View) and a plain-English version (shown in Driver
# View). The functions below generate the plain-English side, so an
# everyday driver never has to interpret a raw number like "SOH: 91%" or
# "Internal Resistance: 118 mOhm" themselves.
# =======================================================================

def condition_word(value: float, good=80, warn=60) -> str:
    """Turns a 0-100 health number into one plain word: Excellent / Good / Fair / Needs Attention."""
    if value >= 90:
        return "Excellent"
    elif value >= good:
        return "Good"
    elif value >= warn:
        return "Fair"
    return "Needs Attention"


def vehicle_status_message(score_info: dict) -> str:
    """One-line plain-English status shown under the big circular score."""
    overall = score_info["overall"]
    if overall >= 90:
        return "Your vehicle is in excellent condition."
    elif overall >= 75:
        return "Your vehicle is in good condition. Minor maintenance may be recommended soon."
    elif overall >= 60:
        return "Your vehicle is in fair condition. Some attention is recommended within the next few weeks."
    return "Your vehicle needs attention. Please review the recommended service items."


def driver_ai_summary(state: dict, score_info: dict) -> str:
    """
    A short natural-language paragraph summarizing the whole vehicle,
    written the way a knowledgeable friend would explain it — no raw
    numbers, no engineering units.
    """
    b, br, d = state["battery"], state["brakes"], state["driver"]
    sentences = []

    if score_info["overall"] >= 85:
        sentences.append("Everything looks healthy today.")
    elif score_info["overall"] >= 70:
        sentences.append("Your vehicle is performing well overall today.")
    else:
        sentences.append("Your vehicle is performing adequately, but a few areas could use attention.")

    battery_word = condition_word(b["health_percent"]).lower()
    if d["eco_score"] >= 70:
        sentences.append(f"Your battery is {battery_word}, and your driving habits are helping preserve battery life.")
    else:
        sentences.append(f"Your battery is {battery_word}, though smoother driving could help it last even longer.")

    if br["pad_wear_pct"] > 55:
        sentences.append("Your brake pads are wearing down and a service should be scheduled soon.")
    elif br["pad_wear_pct"] > 35:
        sentences.append("Your brake pads are wearing normally, but no immediate action is required.")
    else:
        sentences.append("Your brakes are in great shape.")

    if score_info["overall"] >= 85 and br["pad_wear_pct"] <= 55:
        sentences.append("No immediate maintenance is required.")

    return " ".join(sentences)


def estimated_range_km(state: dict, full_range_km: int = 420) -> int:
    """
    Estimates remaining driving range from current charge and battery
    health — the number a driver actually cares about, instead of raw
    State of Charge / State of Health percentages.
    """
    b = state["battery"]
    soc_factor = b["state_of_charge"] / 100
    health_factor = 0.7 + 0.3 * (b["health_percent"] / 100)
    return int(round(full_range_km * soc_factor * health_factor))


def charging_recommendation_text(state: dict) -> list:
    """Plain-language charging guidance for the Battery Card."""
    tips = ["Charge between 20% and 80% for daily use."]
    if state["environment"]["temperature_c"] > 35:
        tips.append("Avoid exposing the vehicle to direct sunlight for long periods today.")
    if state["battery"]["fast_charge_freq_per_week"] >= 5:
        tips.append("Try using regular charging more often than fast charging this week.")
    return tips


def driving_coach(state: dict) -> dict:
    """
    Converts the technical driver-behaviour profile into a friendly
    checklist of what the driver is doing well, plus 1-2 simple
    suggestions — used by the Driving Coach card.
    """
    d, br = state["driver"], state["brakes"]
    positives, suggestions = [], []

    if d["acceleration_aggressiveness"] < 50:
        positives.append("Smooth acceleration today")
    else:
        suggestions.append("Try easing off acceleration a little to increase battery life.")

    if br["regen_efficiency_pct"] >= 70:
        positives.append("Excellent regenerative braking usage")
    else:
        suggestions.append("Coast and use regenerative braking more often to recover extra energy.")

    if d["braking_style"] < 50:
        positives.append("Safe, gentle braking")
    else:
        suggestions.append("Reducing sudden braking will help extend brake life.")

    if d["speed_consistency"] >= 70:
        positives.append("Efficient, steady-speed driving")
    else:
        suggestions.append("Maintain steadier speeds on highways for better efficiency.")

    if not positives:
        positives.append("Keep driving — your coaching tips will appear here as data comes in.")

    return {"positives": positives, "suggestions": suggestions}


def todays_journey(state: dict) -> dict:
    """
    Simplified 'today' trip summary derived from the daily driving
    pattern data, for the Today's Journey card.
    """
    daily, tr = state["daily"], state["traffic"]
    distance = round(daily["commute_distance_km"] * 2, 1)
    driving_time = daily["avg_driving_time_min"] * 2
    energy_used = round(distance * 0.18, 1)
    efficiency = round(clamp_val(100 - tr["energy_lost_pct"]), 1)
    return {
        "trips": 2,
        "distance_km": distance,
        "driving_time_min": driving_time,
        "energy_used_kwh": energy_used,
        "efficiency_pct": efficiency,
    }


def smart_recommendations_driver(state: dict, limit: int = 5) -> list:
    """Driver-facing recommendations — reuses the AI recommendation engine, already in plain language."""
    return generate_recommendations(state)[:limit]


def service_reminder(state: dict) -> dict:
    """Picks the single most relevant upcoming service item, with no technical detail, for the Service Reminder card."""
    maint = state.get("maintenance", {})
    if not maint:
        return {"component": "Vehicle", "distance_km": 5000}

    top_name, top_info = min(maint.items(), key=lambda kv: kv[1]["remaining_life_days"])
    daily_km = max(state["daily"]["weekly_distance_km"] / 7, 5)
    distance_km = int(round(top_info["remaining_life_days"] * daily_km))
    return {"component": top_name, "distance_km": distance_km}


def safety_status(state: dict) -> dict:
    """Simplified ADAS + battery-protection status list for the Safety Status card."""
    adas = state["adas"]

    def status_of(name, default="Active"):
        return adas.get(name, {}).get("status", default)

    return {
        "ADAS": "Active" if any(v["status"] == "Active" for v in adas.values()) else "Inactive",
        "Battery Protection": "Active",
        "Emergency Braking": "Ready" if status_of("Forward Collision Warning") == "Active" else "Inactive",
        "Lane Assist": status_of("Lane Keeping Assist"),
    }


def environment_effect_text(state: dict) -> str:
    """One friendly sentence describing how today's weather/traffic affects range."""
    env, tr = state["environment"], state["traffic"]
    parts = []

    if env["temperature_c"] > 35:
        impact = round((env["temperature_c"] - 25) * 0.3, 1)
        parts.append(f"Today's heat may reduce your range by approximately {impact}%.")

    if tr["density_pct"] > 65:
        traffic_impact = round(tr["energy_lost_pct"], 1)
        parts.append(f"Heavy traffic today may reduce range by approximately {traffic_impact}%.")

    if not parts:
        parts.append("Weather and traffic conditions are having little effect on your range today.")

    return " ".join(parts)


def _status_label(health: float) -> str:
    if health >= 80:
        return "Healthy"
    elif health >= 60:
        return "Needs Attention"
    return "Critical"


def _synthetic_history(seed_key: str, current: float, points: int = 6) -> list:
    """
    Small deterministic random-walk ending near `current`, used purely for
    sparkline history on components that don't have real tracked history
    (e.g. Tires, Suspension, Charging Port, Lights, Doors, ADAS). Seeded
    off the component name so it's stable across reruns of the same state.
    """
    rng = random.Random(abs(hash(seed_key)) % (10**6))
    vals = [current]
    for _ in range(points - 1):
        vals.append(clamp_val(vals[-1] + rng.uniform(-3, 3)))
    vals.reverse()
    return [round(v, 1) for v in vals]


def vehicle_timeline(state: dict, limit: int = 6) -> list:
    """
    Builds a short, plain-language 'Vehicle Timeline' feed for the Vehicle
    section of Driver View — a chronological list of notable events
    (charging sessions, trips, alerts, AI checks) derived from the current
    simulated state. Purely presentational; timestamps are relative to
    now so the feed always looks fresh regardless of when it's viewed.
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    b, d, trip = state["battery"], state["driver"], state.get("trip", {})
    events = []

    events.append((now - timedelta(minutes=2), f"AI analysis completed — overall vehicle condition {condition_word(overall_vehicle_score(state)['overall']).lower()}."))

    if trip.get("distance_km", 0) > 0.5:
        events.append((now - timedelta(minutes=8), f"Trip in progress toward {trip.get('destination', 'destination')} — {round(trip.get('distance_km', 0), 1)} km so far."))

    if b["state_of_charge"] < 30:
        events.append((now - timedelta(hours=1), "Battery charge is getting low — consider charging soon."))
    else:
        events.append((now - timedelta(hours=6), f"Charging session completed — battery reached {round(b['state_of_charge'])}%."))

    if d["acceleration_aggressiveness"] > 60:
        events.append((now - timedelta(hours=2), "AI Driving Coach noted a few harder acceleration events today."))
    else:
        events.append((now - timedelta(hours=3), "Smooth driving detected — battery stress kept low."))

    if state["alerts"] and "No critical alerts" not in state["alerts"][0]:
        events.append((now - timedelta(hours=4), f"Vehicle Care flagged: {state['alerts'][0]}"))

    events.append((now - timedelta(days=1), "Daily AI health check completed — no critical issues found."))

    events.sort(key=lambda e: e[0], reverse=True)
    return [{"time": t.strftime("%I:%M %p") if (now - t).days < 1 else t.strftime("%b %d"), "text": text}
            for t, text in events[:limit]]


def component_health_map(state: dict) -> dict:
    """
    Builds the full data set behind the Interactive Vehicle Visualization:
    one entry per physical component (Battery, Motor, Brakes, Tires,
    Suspension, Charging Port, Lights, ADAS, Doors), each with a health
    score, a Healthy/Needs Attention/Critical status, a plain-language
    recommendation, an upcoming-service estimate, and a short history for
    a sparkline — everything the "click a component" detail panel needs.
    """
    b, m, br = state["battery"], state["motor"], state["brakes"]
    tires, sus, ch, adas = state["tires"], state["suspension"], state["charging"], state["adas"]
    maint = state.get("maintenance", {})

    tire_health = round(clamp_val(100 - (sum(tires["wear_pct"]) / 4)), 1)
    adas_health = round(clamp_val(sum(v["health"] for v in adas.values()) / max(len(adas), 1)), 1)
    charging_health = round(clamp_val(100 - ch["stress_from_charging"]), 1)
    lights_health = 97.0
    doors_health = 100.0

    def service_text(name, fallback_km):
        info = maint.get(name)
        if not info:
            return f"~{fallback_km:,} km"
        daily_km = max(state["daily"]["weekly_distance_km"] / 7, 5)
        return f"~{int(info['remaining_life_days'] * daily_km):,} km"

    components = {
        "Battery": {
            "health": b["health_percent"],
            "recommendation": (b["recommendations"][0] if b["recommendations"] else "Battery is performing well."),
            "service": service_text("Battery", 15000),
            "history": state["history"]["battery_health"][-6:] or _synthetic_history("battery", b["health_percent"]),
        },
        "Motor": {
            "health": m["health_pct"],
            "recommendation": "Inspect motor cooling and bearings soon." if m["health_pct"] < 85 else "Motor performing normally.",
            "service": service_text("Motor", 12000),
            "history": state["history"]["motor_health"][-6:] or _synthetic_history("motor", m["health_pct"]),
        },
        "Brakes": {
            "health": round(clamp_val(100 - br["pad_wear_pct"]), 1),
            "recommendation": (
                "Schedule a brake inspection soon." if (100 - br["pad_wear_pct"]) < 60
                else "Monitor brake wear over the coming weeks." if (100 - br["pad_wear_pct"]) < 80
                else "Brakes performing normally."
            ),
            "service": service_text("Brakes", 6000),
            "history": [round(100 - v, 1) for v in state["history"]["brake_wear"][-6:]] or _synthetic_history("brakes", 100 - br["pad_wear_pct"]),
        },
        "Tires": {
            "health": tire_health,
            "recommendation": "Tire rotation recommended soon." if tire_health < 75 else "Tires in good condition.",
            "service": f"~{tires['rotation_due_km']:,} km",
            "history": _synthetic_history("tires", tire_health),
        },
        "Suspension": {
            "health": sus["shock_health_pct"],
            "recommendation": "Suspension performing normally." if sus["shock_health_pct"] >= 75 else "Suspension inspection recommended.",
            "service": service_text("Suspension", 10000),
            "history": _synthetic_history("suspension", sus["shock_health_pct"]),
        },
        "Charging Port": {
            "health": charging_health,
            "recommendation": "Charging system operating efficiently." if charging_health >= 75 else "Consider reducing fast-charge frequency.",
            "service": service_text("Charging Port", 20000),
            "history": _synthetic_history("charging", charging_health),
        },
        "Lights": {
            "health": lights_health,
            "recommendation": "All exterior lighting operating normally.",
            "service": "~25,000 km",
            "history": _synthetic_history("lights", lights_health),
        },
        "ADAS": {
            "health": adas_health,
            "recommendation": "Driver-assist systems fully calibrated." if adas_health >= 85 else "ADAS calibration recommended at next service.",
            "service": "~18,000 km",
            "history": _synthetic_history("adas", adas_health),
        },
        "Doors": {
            "health": doors_health,
            "recommendation": "All doors and locks functioning normally.",
            "service": "No action needed",
            "history": _synthetic_history("doors", doors_health),
        },
    }

    for info in components.values():
        info["health"] = round(clamp_val(info["health"]), 1)
        info["status"] = _status_label(info["health"])

    return components


# ---------------------------------------------------------------------
# Charging (Driver View - Charging section)
# ---------------------------------------------------------------------

CHARGING_MODES = {
    "Eco Charge": {"icon": "🌱", "sub": "Slow, battery-friendly", "rate_kw": 7},
    "Balanced Charge": {"icon": "⚖️", "sub": "Everyday recommended", "rate_kw": 11},
    "Rapid Charge": {"icon": "⚡", "sub": "Fast, higher battery stress", "rate_kw": 50},
}


def smart_charging_recommendation(state: dict) -> dict:
    """
    Picks the AI-recommended charging mode for right now and a one-line
    plain-language reason, used by the AI Smart Charging card.
    """
    b = state["battery"]
    trip = state.get("trip", {})

    if b["state_of_charge"] < 25 and trip.get("eta_min", 0) < 20:
        mode = "Rapid Charge"
        reason = "Battery is low and you have a trip coming up soon — Rapid Charge will get you ready faster."
    elif b["fast_charge_freq_per_week"] >= 5 or b["stress_index"] > 55:
        mode = "Eco Charge"
        reason = "You've used fast charging often this week — Eco Charge tonight will help the battery recover."
    else:
        mode = "Balanced Charge"
        reason = "Balanced Charge is recommended today because you have sufficient time before your next trip."

    return {"mode": mode, "reason": reason}


def charging_history(state: dict) -> list:
    """Builds a short, plausible recent charging session history for the Charging History card."""
    from datetime import datetime, timedelta
    rng = random.Random(11)
    b = state["battery"]
    now = datetime.now()
    sessions = []
    for i in range(5):
        day = now - timedelta(days=i + 1)
        start_pct = rng.randint(15, 45)
        end_pct = rng.randint(70, 100)
        mode = rng.choice(list(CHARGING_MODES.keys()))
        cost = round((end_pct - start_pct) / 100 * 60 * rng.uniform(6.5, 9.5), 0)
        sessions.append({
            "date": day.strftime("%b %d"),
            "mode": mode,
            "from_pct": start_pct,
            "to_pct": end_pct,
            "cost_inr": int(cost),
        })
    return sessions


def charging_optimization_tips(state: dict) -> list:
    """Battery-protection / optimization guidance for the Charging section."""
    tips = [
        "Charging between 20% and 80% daily reduces long-term battery wear.",
        "Avoid charging immediately after aggressive driving — let the battery cool first.",
    ]
    if state["environment"]["temperature_c"] > 35:
        tips.append("High ambient temperature detected — charging speed may be automatically reduced to protect the battery.")
    if state["battery"]["fast_charge_freq_per_week"] >= 5:
        tips.append("Frequent fast charging detected — alternating with slower overnight charging is recommended.")
    return tips


# ---------------------------------------------------------------------
# Drive Intelligence (Driver View - Drive Intelligence section)
# ---------------------------------------------------------------------

def driving_score_breakdown(state: dict) -> dict:
    """Plain-language driving/eco/safety scores plus behaviour breakdown for the Drive Intelligence section."""
    d = state["driver"]
    return {
        "driving_score": round((d["safety_score"] + d["eco_score"] + d["confidence_score"]) / 3, 1),
        "eco_score": d["eco_score"],
        "safety_score": d["safety_score"],
        "acceleration": round(clamp_val(100 - d["acceleration_aggressiveness"]), 1),
        "braking": round(clamp_val(100 - d["braking_style"]), 1),
        "cornering": d["cornering"],
        "energy_efficiency": round(clamp_val(100 - state["traffic"]["energy_lost_pct"] - (0 if d["eco_score"] > 70 else 8)), 1),
    }


def driving_suggestions(state: dict) -> list:
    """A short list of specific, plain-language driving suggestions."""
    d = state["driver"]
    tips = []
    if d["acceleration_aggressiveness"] > 55:
        tips.append("Easing into acceleration rather than flooring it can meaningfully extend battery life.")
    if d["braking_style"] > 55:
        tips.append("Try anticipating stops earlier to brake more gradually and reduce brake wear.")
    if d["cornering"] < 60:
        tips.append("Taking corners a little more gently will improve ride comfort and tire wear.")
    if d["speed_consistency"] < 65:
        tips.append("Holding a steadier speed on highways improves efficiency more than most drivers expect.")
    if not tips:
        tips.append("Your driving style is already efficient — keep it up.")
    return tips


# ---------------------------------------------------------------------
# Smart Assist (Driver View - renamed ADAS features)
# ---------------------------------------------------------------------

SMART_ASSIST_RENAME = {
    "Lane Keeping Assist": "Precision Steering Assist",
    "Blind Spot Detection": "Blind Spot Monitoring",
    "Forward Collision Warning": "Emergency Braking",
    "Adaptive Cruise Control": "Adaptive Cruise AI",
    "Traffic Sign Recognition": "Traffic Sign Recognition",
    "Driver Monitoring": "Driver Attention Monitor",
    "Automatic Emergency Braking": "Intelligent Drive Pilot",
    "Parking Assist": "Smart Parking Assist",
    "Pedestrian Detection": "Pedestrian Detection",
}

SMART_ASSIST_EXTRAS = [
    ("Smart Lane Transition", "Balanced", "Automatically changes lanes when safe to do so."),
    ("Adaptive Headlights", "Active", "Adjusts beam direction and range with steering and speed."),
    ("Auto High Beam", "Active", "Automatically toggles high beams based on oncoming traffic."),
    ("Automatic Flash-to-Pass", "Active", "Briefly flashes headlights when passing is detected."),
    ("Rain-Sensing Wipers", "Active", "Automatically adjusts wiper speed to rainfall intensity."),
]

LANE_CHANGE_PROFILES = ["Gentle", "Balanced", "Dynamic"]


def smart_assist_features(state: dict) -> list:
    """
    Builds the full Smart Assist feature list with premium names, reusing
    the existing ADAS health/confidence data so Insights View and Driver
    View stay numerically consistent, plus a few extra convenience
    features not tracked elsewhere.
    """
    adas = state["adas"]
    features = []
    for original_name, premium_name in SMART_ASSIST_RENAME.items():
        info = adas.get(original_name, {"status": "Active", "health": 90, "confidence": 88})
        features.append({
            "name": premium_name,
            "status": info["status"],
            "health": info["health"],
            "confidence": info["confidence"],
        })
    for name, status, desc in SMART_ASSIST_EXTRAS:
        features.append({"name": name, "status": status, "health": None, "confidence": None, "desc": desc})
    return features


# ---------------------------------------------------------------------
# Comfort (Driver View - Comfort section)
# ---------------------------------------------------------------------

def comfort_recommendation(state: dict) -> dict:
    """
    AI-optimized cabin comfort settings based on current weather and
    battery efficiency considerations, plus the reasoning behind them.
    """
    env, b = state["environment"], state["battery"]
    temp = env["temperature_c"]

    if temp > 32:
        cabin_target = 23
        climate_mode = "Cooling"
        seats = "Ventilated Seats On"
    elif temp < 18:
        cabin_target = 22
        climate_mode = "Heating"
        seats = "Heated Seats On"
    else:
        cabin_target = 24
        climate_mode = "Auto"
        seats = "Off"

    eco_note = (
        "Climate control power has been slightly reduced to preserve battery range."
        if b["state_of_charge"] < 30 else
        "Climate control is running at full comfort since battery charge is sufficient."
    )

    return {
        "cabin_target_c": cabin_target,
        "climate_mode": climate_mode,
        "seats": seats,
        "air_quality": "Good" if env["air_quality_index"] < 100 else "Moderate",
        "note": eco_note,
    }


# ---------------------------------------------------------------------
# Vehicle Care (Driver View - AI inspection center)
# ---------------------------------------------------------------------

VEHICLE_CARE_CATALOG = [
    {"issue": "Wheel Misalignment", "component": "Steering & Wheels", "cause": "Repeated impacts from potholes.",
     "driver_fixable": False, "action": "Schedule wheel alignment. Until then avoid aggressive cornering.",
     "repair_time_min": 45, "cost_inr": (800, 1500)},
    {"issue": "Uneven Tire Wear", "component": "Tires", "cause": "Under-inflation or misalignment over time.",
     "driver_fixable": True, "action": "Check and correct tire pressure; rotate tires at next service.",
     "repair_time_min": 20, "cost_inr": (0, 600)},
    {"issue": "Possible Tire Puncture", "component": "Tires", "cause": "Sharp road debris detected in tire pressure pattern.",
     "driver_fixable": False, "action": "Inspect tire visually and visit a service center soon.",
     "repair_time_min": 30, "cost_inr": (300, 900)},
    {"issue": "Brake Oil Leakage", "component": "Brake System", "cause": "Worn brake line seal or fitting.",
     "driver_fixable": False, "action": "Visit a service center promptly — do not delay.",
     "repair_time_min": 60, "cost_inr": (1200, 2500)},
    {"issue": "Low Coolant", "component": "Cooling System", "cause": "Gradual evaporation or a minor leak.",
     "driver_fixable": True, "action": "Top up coolant and monitor for recurring loss.",
     "repair_time_min": 15, "cost_inr": (200, 500)},
    {"issue": "Suspension Wear", "component": "Suspension", "cause": "High mileage on rough roads.",
     "driver_fixable": False, "action": "Schedule a suspension inspection within the next month.",
     "repair_time_min": 90, "cost_inr": (2000, 4500)},
    {"issue": "Motor Cooling Issue", "component": "Motor", "cause": "Reduced coolant flow or fan efficiency.",
     "driver_fixable": False, "action": "Avoid sustained high-speed driving until inspected.",
     "repair_time_min": 60, "cost_inr": (1500, 3000)},
    {"issue": "Charging Port Damage", "component": "Charging Port", "cause": "Repeated connector wear or moisture exposure.",
     "driver_fixable": False, "action": "Avoid charging until the port is inspected.",
     "repair_time_min": 40, "cost_inr": (800, 2000)},
    {"issue": "Headlight Damage", "component": "Exterior Lighting", "cause": "Minor impact or vibration over time.",
     "driver_fixable": True, "action": "Replace headlight bulb/housing at your convenience.",
     "repair_time_min": 25, "cost_inr": (400, 1200)},
    {"issue": "Windshield Crack", "component": "Windshield", "cause": "Stone chip that has propagated.",
     "driver_fixable": False, "action": "Schedule windshield repair before the crack spreads further.",
     "repair_time_min": 60, "cost_inr": (1500, 4000)},
    {"issue": "Exterior Dent Detection", "component": "Body Panel", "cause": "Minor parking or door impact.",
     "driver_fixable": False, "action": "Cosmetic only — repair at your convenience.",
     "repair_time_min": 45, "cost_inr": (1000, 3000)},
    {"issue": "Camera Lens Dirty", "component": "ADAS Sensors", "cause": "Road dust or grime buildup.",
     "driver_fixable": True, "action": "Clean the camera lens with a soft microfiber cloth.",
     "repair_time_min": 5, "cost_inr": (0, 0)},
    {"issue": "Radar Calibration Required", "component": "ADAS Sensors", "cause": "Minor sensor drift detected after a recent bump.",
     "driver_fixable": False, "action": "Schedule a radar recalibration at your next service visit.",
     "repair_time_min": 30, "cost_inr": (500, 1200)},
    {"issue": "Loose Underbody Shield", "component": "Underbody", "cause": "Fastener loosened from road vibration.",
     "driver_fixable": True, "action": "Have the shield refastened at your next stop — avoid rough roads meanwhile.",
     "repair_time_min": 15, "cost_inr": (0, 400)},
    {"issue": "Battery Cooling Issue", "component": "Battery Pack", "cause": "Reduced coolant circulation efficiency.",
     "driver_fixable": False, "action": "Avoid fast charging until the cooling system is inspected.",
     "repair_time_min": 60, "cost_inr": (1800, 3500)},
]


def vehicle_care_diagnostics(state: dict) -> list:
    """
    Simulates an AI inspection pass: selects a plausible handful of
    issues (more when overall health is lower, fewer when the vehicle is
    healthy) from the catalog above, and attaches severity + AI diagnosis
    text. Deterministic-ish per session via a fixed seed so the same
    issues don't reshuffle on every widget interaction, only on tick().
    """
    score = overall_vehicle_score(state)["overall"]
    rng = random.Random(int(state["battery"]["health_percent"] * 100) + int(state["motor"]["health_pct"]))

    num_issues = 1 if score >= 90 else 2 if score >= 75 else 4 if score >= 60 else 6
    chosen = rng.sample(VEHICLE_CARE_CATALOG, k=min(num_issues, len(VEHICLE_CARE_CATALOG)))

    results = []
    for item in chosen:
        severity = rng.choices(["Minor", "Moderate", "Severe"], weights=[0.5, 0.35, 0.15])[0]
        cost_lo, cost_hi = item["cost_inr"]
        results.append({
            **item,
            "severity": severity,
            "diagnosis": f"AI detected early signs of {item['issue'].lower()} based on sensor pattern analysis.",
            "repair_cost_inr": f"₹{cost_lo}–₹{cost_hi}" if cost_hi > 0 else "No cost (self-service)",
        })
    return results


# ---------------------------------------------------------------------
# Settings (Driver View - Settings section)
# ---------------------------------------------------------------------

def edge_ai_status(state: dict) -> dict:
    """Static-ish Edge AI system status info for the Settings section."""
    return {
        "model": "Battery Health Random Forest (local)",
        "processing": "100% on-device — no cloud calls",
        "last_sync": "Not applicable (offline)",
        "data_stored_locally": "Yes",
    }


# ---------------------------------------------------------------------
# AI Welcome Experience (Driver View home screen)
# ---------------------------------------------------------------------

def time_of_day() -> str:
    """Returns 'morning', 'afternoon', 'evening', or 'night' for greetings and theming."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    return "night"


def current_theme_condition(state: dict) -> str:
    """
    Picks the single most relevant subtle ambient theme condition for
    dynamic_theme_overlay_css: charging beats weather beats time-of-day,
    since it's the most visually distinctive and temporary state.
    """
    if state["battery"].get("state_of_charge", 100) < 100 and state.get("_charging_now"):
        return "charging"
    if state["environment"]["weather"] in ("Rain",):
        return "rain"
    tod = time_of_day()
    if tod == "night":
        return "night"
    if tod == "morning":
        return "morning"
    return "day"


def ai_greeting(state: dict, driver_name: str = "Driver") -> dict:
    """
    Builds the personalized AI welcome message shown when Driver View
    first loads, rotating its supporting detail based on simulated time
    of day, weather, traffic, and battery — e.g. 'Good Morning, Driver.
    Battery level is healthy. Traffic is moderate.'
    """
    tod = time_of_day()
    greeting_word = {"morning": "Good Morning", "afternoon": "Good Afternoon",
                      "evening": "Good Evening", "night": "Good Evening"}[tod]

    b = state["battery"]
    env = state["environment"]
    details = []

    if b["state_of_charge"] >= 70:
        details.append("Your vehicle is ready.")
    elif b["state_of_charge"] >= 30:
        details.append("Battery level is healthy.")
    else:
        details.append("Battery is getting low — consider charging soon.")

    if env["weather"] == "Rain":
        details.append("Rain is expected today.")
    elif env["temperature_c"] > 34:
        details.append(f"Today's weather is warm at {round(env['temperature_c'])}°C.")
    else:
        details.append(f"Today's weather is pleasant at {round(env['temperature_c'])}°C.")

    if env["traffic_level"] == "Heavy":
        details.append("Traffic is heavy on your usual route.")
        details.append("Eco Drive is recommended.")
    elif env["traffic_level"] == "Moderate":
        details.append("Traffic is moderate today.")
    else:
        details.append("Roads are clear right now.")

    rng = random.Random(int(datetime.now().timestamp()) // 20)  # rotates roughly every ~20s
    detail = rng.choice(details)

    return {"title": f"{greeting_word}, {driver_name}.", "detail": detail}


def ai_mood(score_info: dict) -> dict:
    """
    Replaces a raw health percentage with a friendly emoji + status label
    for the Driver View Mood Indicator.
    """
    overall = score_info["overall"]
    if overall >= 92:
        return {"emoji": "🟢", "text": "Performing Excellent"}
    elif overall >= 80:
        return {"emoji": "🟢", "text": "Ready for the Road"}
    elif overall >= 65:
        return {"emoji": "🟡", "text": "Needs Some Attention"}
    elif overall >= 50:
        return {"emoji": "🟡", "text": "Service Recommended Soon"}
    return {"emoji": "🔴", "text": "Immediate Inspection Required"}


def vehicle_summary_sentences(state: dict, score_info: dict) -> list:
    """
    A short, varied natural-language vehicle summary for the Driver View
    home screen — 2-3 plain-English sentences, no raw percentages, that
    change with the simulated state (and rotate slightly in wording so
    Demo Mode doesn't feel repetitive).
    """
    b, br, d = state["battery"], state["brakes"], state["driver"]
    lines = []

    if score_info["overall"] >= 88:
        lines.append(random.choice([
            "Your vehicle is performing optimally today.",
            "Everything is running smoothly today.",
        ]))
    elif score_info["overall"] >= 70:
        lines.append("Your vehicle is performing well today.")
    else:
        lines.append("Your vehicle could use a bit of attention today.")

    if b["temperature"] <= 38:
        lines.append("Battery temperature is ideal.")
    else:
        lines.append("Battery temperature is a little high — nothing urgent yet.")

    if br["pad_wear_pct"] < 40 and score_info["overall"] >= 75:
        lines.append("No maintenance is currently required.")
    elif br["pad_wear_pct"] > 55:
        lines.append("A brake service should be scheduled soon.")

    if d["eco_score"] >= 70:
        lines.append("Driving habits have been efficient recently.")

    return lines[:3]


def companion_messages(state: dict) -> list:
    """
    Builds the rotating message list for the floating AI Companion —
    short, specific, vehicle-companion-style insights (not a chatbot).
    """
    b, br, env, tr = state["battery"], state["brakes"], state["environment"], state["traffic"]
    trip = state.get("trip", {})
    msgs = []

    if tr["density_pct"] > 60:
        msgs.append("Heavy traffic ahead. Eco Drive is recommended.")
    if trip.get("energy_recovered_kwh", 0) > 0.05:
        msgs.append(f"You've recovered {trip['energy_recovered_kwh']:.1f} kWh using regenerative braking today.")
    msgs.append("Battery cooling is operating efficiently." if b["temperature"] < 40 else "Battery is running a little warm — cooling is compensating.")
    if env["weather"] == "Rain":
        msgs.append("Rain expected shortly — road grip may be reduced.")
    if b["state_of_charge"] < 50:
        msgs.append("Charging after today's commute is recommended.")
    if br["regen_efficiency_pct"] > 70:
        msgs.append("Regenerative braking efficiency is excellent today.")
    msgs.append(f"Eco driving score is {state['driver']['eco_score']}% today.")

    if not msgs:
        msgs.append("All systems normal. Enjoy your drive.")
    return msgs


def smart_notification(state: dict) -> str:
    """
    Picks one short, elegant status notification (for st.toast) reflecting
    something that just happened in the simulated state — used instead of
    a traditional alert popup.
    """
    b, tr, br = state["battery"], state["traffic"], state["brakes"]
    candidates = []
    if state["driver"]["eco_score"] > 70:
        candidates.append("✓ Eco Mode enabled")
    if b["charging_efficiency"] > 90:
        candidates.append("✓ Battery charging optimized")
    candidates.append("✓ Tire pressure checked")
    if tr["density_pct"] > 65:
        candidates.append("✓ Traffic rerouted")
    if not state["alerts"] or "No critical" in state["alerts"][0]:
        candidates.append("✓ Vehicle inspection completed")
    return random.choice(candidates)


def journey_timeline_narrative(state: dict) -> list:
    """
    A chronological, story-like journey timeline for the Vehicle section —
    'Vehicle Started -> Traffic Detected -> AI Enabled Eco Driving ->
    Regenerative Braking Recovered Energy -> Destination Reached' — built
    from the current simulated trip/traffic/driving state so it updates
    naturally during Demo Mode.
    """
    trip, tr, d = state.get("trip", {}), state["traffic"], state["driver"]
    steps = ["🚗 Vehicle Started"]

    if tr["density_pct"] > 45:
        steps.append("🚦 Traffic Detected")
        steps.append("🌿 AI Enabled Eco Driving")
    if trip.get("energy_recovered_kwh", 0) > 0.02:
        steps.append("🔋 Regenerative Braking Recovered Energy")
    if d["acceleration_aggressiveness"] < 45:
        steps.append("✅ Smooth Driving Maintained")
    if trip.get("distance_km", 0) > 0.3:
        steps.append(f"📍 {round(trip.get('distance_km', 0), 1)} km Travelled Toward {trip.get('destination', 'Destination')}")
    if trip.get("eta_min", 99) < 5:
        steps.append("🏁 Destination Reached")

    return steps


def before_driving_notes(state: dict) -> list:
    """
    The 'What should I know before driving?' bullet list for the Driver
    View home screen — at most 3 short, plain-language items, prioritized
    by relevance (weather/traffic/top AI recommendation).
    """
    env, tr = state["environment"], state["traffic"]
    notes = []
    if env["weather"] == "Rain":
        notes.append("Roads may be wet — drive with extra care.")
    if tr["density_pct"] > 60:
        notes.append("Heavier traffic than usual is expected on your route.")
    top_recs = smart_recommendations_driver(state, limit=1)
    if top_recs:
        notes.append(top_recs[0])
    if not notes:
        notes.append("Conditions look good — enjoy your drive.")
    return notes[:3]
