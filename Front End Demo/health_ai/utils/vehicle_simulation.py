"""
vehicle_simulation.py
----------------------
Generates and evolves a single, internally-consistent synthetic "vehicle
state" covering every subsystem the platform demonstrates: battery,
motor, brakes, tires, suspension, driver behaviour, daily driving
patterns, environment, traffic, ADAS, predictive maintenance, and
charging. Where a real trained model exists (the Battery Health Random
Forest), it is used; everything else is realistic simulated data, since
building real sensors/telemetry for a motor, brakes, ADAS, etc. is out of
scope for a local demo.

The state lives in Streamlit's session_state so it persists across
reruns, and `tick()` nudges it forward in time (used both for normal
interaction and for Demo Mode's live simulation).
"""

import os
import random
import sys
from datetime import datetime, timedelta

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from inference.predict import BatteryHealthPredictor

_predictor_cache = None


def get_predictor():
    """Lazily loads and caches the trained battery model (avoids reload every tick)."""
    global _predictor_cache
    if _predictor_cache is None:
        _predictor_cache = BatteryHealthPredictor()
    return _predictor_cache


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def init_vehicle_state() -> dict:
    """
    Builds the initial synthetic vehicle state. Called once per session.
    All values are intentionally set to look like a moderately-used EV
    (not brand new, not near end-of-life) so every panel has something
    interesting to show immediately.
    """
    rng = random.Random(7)

    raw_battery_inputs = {
        "voltage": 378.0,
        "temperature": 33.0,
        "state_of_charge": 62.0,
        "charge_cycles": 640.0,
        "current": -35.0,
        "battery_age_months": 22.0,
        "internal_resistance": 42.0,
        "ambient_temperature": 29.0,
    }
    battery_result = get_predictor().predict(**raw_battery_inputs)

    state = {
        "last_analysis_time": datetime.now(),

        "battery": {
            **raw_battery_inputs,
            "health_percent": battery_result["battery_health_percent"],
            "status": battery_result["status"],
            "factors": battery_result["factors"],
            "recommendations": battery_result["recommendations"],
            "soh": round(battery_result["battery_health_percent"] - rng.uniform(0, 2), 1),
            "sop_kw": round(rng.uniform(85, 120), 1),
            "remaining_cycles": int(max(0, 2200 - raw_battery_inputs["charge_cycles"])),
            "cell_temp_spread_c": round(rng.uniform(1.0, 4.5), 1),
            "charging_efficiency": round(rng.uniform(88, 96), 1),
            "discharging_efficiency": round(rng.uniform(90, 97), 1),
            "fast_charge_freq_per_week": rng.randint(1, 6),
            "stress_index": round(rng.uniform(20, 60), 1),
            "thermal_risk": "Low",
            "replacement_eta_months": int(max(6, 96 - raw_battery_inputs["battery_age_months"])),
        },

        "motor": {
            "temperature_c": round(rng.uniform(45, 70), 1),
            "efficiency_pct": round(rng.uniform(88, 96), 1),
            "rpm": rng.randint(2500, 6500),
            "torque_nm": round(rng.uniform(150, 320), 1),
            "bearing_health_pct": round(rng.uniform(75, 98), 1),
            "cooling_status": "Normal",
            "vibration_mm_s": round(rng.uniform(0.5, 3.0), 2),
            "remaining_life_pct": round(rng.uniform(70, 95), 1),
            "health_pct": round(rng.uniform(80, 96), 1),
        },

        "brakes": {
            "pad_wear_pct": round(rng.uniform(15, 55), 1),
            "disc_wear_pct": round(rng.uniform(10, 40), 1),
            "temperature_c": round(rng.uniform(60, 140), 1),
            "fluid_status_pct": round(rng.uniform(75, 100), 1),
            "efficiency_pct": round(rng.uniform(85, 98), 1),
            "regen_efficiency_pct": round(rng.uniform(55, 80), 1),
            "mechanical_ratio_pct": round(rng.uniform(20, 45), 1),
            "service_distance_km": rng.randint(500, 6000),
        },

        "tires": {
            "pressure_psi": [round(rng.uniform(30, 36), 1) for _ in range(4)],
            "temperature_c": [round(rng.uniform(28, 45), 1) for _ in range(4)],
            "wear_pct": [round(rng.uniform(10, 45), 1) for _ in range(4)],
            "alignment_status": "Good",
            "rotation_due_km": rng.randint(500, 4000),
            "remaining_life_km": rng.randint(8000, 30000),
        },

        "suspension": {
            "shock_health_pct": round(rng.uniform(70, 96), 1),
            "vibration_score": round(rng.uniform(10, 40), 1),
            "ride_comfort_score": round(rng.uniform(65, 95), 1),
            "road_impact_events_week": rng.randint(2, 15),
        },

        "driver": {
            "acceleration_aggressiveness": round(rng.uniform(20, 80), 1),
            "braking_style": round(rng.uniform(20, 80), 1),
            "cornering": round(rng.uniform(30, 90), 1),
            "steering_smoothness": round(rng.uniform(40, 95), 1),
            "speed_consistency": round(rng.uniform(40, 95), 1),
            "reaction_time_ms": rng.randint(220, 480),
            "night_driving_pct": round(rng.uniform(5, 35), 1),
            "rain_driving_pct": round(rng.uniform(2, 20), 1),
            "confidence_score": round(rng.uniform(60, 95), 1),
            "safety_score": round(rng.uniform(65, 97), 1),
            "eco_score": round(rng.uniform(50, 90), 1),
        },

        "daily": {
            "most_frequent_route": "Home -> MIT Campus -> Home",
            "commute_distance_km": round(rng.uniform(12, 35), 1),
            "avg_driving_time_min": rng.randint(25, 70),
            "preferred_departure": "08:15 AM",
            "preferred_arrival": "09:05 AM",
            "most_visited": ["Home", "Campus", "Grocery Store", "Gym"],
            "weekly_distance_km": round(rng.uniform(120, 320), 1),
            "monthly_distance_km": round(rng.uniform(500, 1300), 1),
            "avg_speed_kmh": round(rng.uniform(28, 55), 1),
            "peak_speed_kmh": round(rng.uniform(70, 110), 1),
            "idle_time_pct": round(rng.uniform(8, 25), 1),
            "city_pct": round(rng.uniform(45, 80), 1),
        },

        "environment": {
            "city": "Chennai",
            "temperature_c": round(rng.uniform(27, 38), 1),
            "humidity_pct": round(rng.uniform(50, 85), 1),
            "air_quality_index": rng.randint(60, 160),
            "weather": "Partly Cloudy",
            "road_surface": "Dry Asphalt",
            "traffic_level": "Moderate",
            "elevation_m": rng.randint(5, 40),
            "wind_kmh": round(rng.uniform(3, 20), 1),
        },

        "traffic": {
            "density_pct": round(rng.uniform(30, 85), 1),
            "congestion_score": round(rng.uniform(20, 80), 1),
            "avg_delay_min": round(rng.uniform(3, 22), 1),
            "avg_stop_time_min": round(rng.uniform(2, 15), 1),
            "frequent_zones": ["Guindy Junction", "Kathipara Flyover", "Anna University Signal"],
            "energy_lost_pct": round(rng.uniform(3, 12), 1),
        },

        "adas": {
            "Lane Keeping Assist": {"status": "Active", "health": 96, "confidence": 94},
            "Blind Spot Detection": {"status": "Active", "health": 92, "confidence": 90},
            "Forward Collision Warning": {"status": "Active", "health": 98, "confidence": 95},
            "Adaptive Cruise Control": {"status": "Active", "health": 91, "confidence": 89},
            "Traffic Sign Recognition": {"status": "Active", "health": 88, "confidence": 85},
            "Driver Monitoring": {"status": "Active", "health": 95, "confidence": 93},
            "Automatic Emergency Braking": {"status": "Active", "health": 97, "confidence": 96},
            "Parking Assist": {"status": "Active", "health": 90, "confidence": 88},
            "Pedestrian Detection": {"status": "Active", "health": 93, "confidence": 91},
        },

        "charging": {
            "optimal_window": "11:30 PM - 5:30 AM",
            "recommended_soc_pct": "20% - 80%",
            "cost_estimate_inr": round(rng.uniform(90, 220), 0),
            "fast_charge_recommendation": "Use only when trip distance exceeds daily range buffer",
            "slow_charge_recommendation": "Preferred for daily overnight charging",
            "stress_from_charging": round(rng.uniform(15, 45), 1),
        },

        "trip": {
            "destination": "MIT Campus",
            "distance_km": 0.0,
            "duration_min": 0.0,
            "current_speed_kmh": 0.0,
            "avg_speed_kmh": 0.0,
            "peak_speed_kmh": 0.0,
            "energy_used_kwh": 0.0,
            "energy_recovered_kwh": 0.0,
            "idle_time_min": 0.0,
            "eta_min": 32.0,
        },

        "alerts": [],

        "history": {
            "t": [],
            "battery_health": [],
            "motor_health": [],
            "brake_wear": [],
            "energy_consumption": [],
            "driving_score": [],
            "efficiency": [],
            "daily_distance": [],
            "temperature": [],
            "traffic_impact": [],
        },
    }

    # Seed 30 days of history so trend charts aren't empty on first load.
    now = datetime.now()
    for i in range(30, 0, -1):
        t = now - timedelta(days=i)
        state["history"]["t"].append(t.strftime("%b %d"))
        state["history"]["battery_health"].append(round(state["battery"]["health_percent"] + rng.uniform(-1.5, 1.5) + i * 0.03, 1))
        state["history"]["motor_health"].append(round(state["motor"]["health_pct"] + rng.uniform(-2, 2), 1))
        state["history"]["brake_wear"].append(round(state["brakes"]["pad_wear_pct"] - i * 0.15 + rng.uniform(-1, 1), 1))
        state["history"]["energy_consumption"].append(round(rng.uniform(12, 22), 1))
        state["history"]["driving_score"].append(round(state["driver"]["safety_score"] + rng.uniform(-4, 4), 1))
        state["history"]["efficiency"].append(round(rng.uniform(78, 94), 1))
        state["history"]["daily_distance"].append(round(rng.uniform(15, 60), 1))
        state["history"]["temperature"].append(round(state["environment"]["temperature_c"] + rng.uniform(-3, 3), 1))
        state["history"]["traffic_impact"].append(round(rng.uniform(3, 14), 1))

    state["recommendations"] = []
    state["alerts"] = []
    _refresh_derived(state)
    return state


# ---------------------------------------------------------------------
# Live simulation tick (used by Demo Mode and manual refresh)
# ---------------------------------------------------------------------

def tick(state: dict):
    """
    Advances the simulated vehicle state by one small time step, mutating
    it in place. Uses small random walks so values drift realistically
    rather than jumping randomly every refresh.
    """
    rng = random.Random()

    b = state["battery"]
    b["state_of_charge"] = clamp(b["state_of_charge"] + rng.uniform(-4, 2), 5, 100)
    b["temperature"] = clamp(b["temperature"] + rng.uniform(-1, 1.2), 15, 55)
    b["current"] = clamp(b["current"] + rng.uniform(-8, 8), -150, 60)
    b["charge_cycles"] = b["charge_cycles"] + rng.uniform(0, 0.3)

    result = get_predictor().predict(
        voltage=b["voltage"], temperature=b["temperature"], state_of_charge=b["state_of_charge"],
        charge_cycles=b["charge_cycles"], current=b["current"], battery_age_months=b["battery_age_months"],
        internal_resistance=b["internal_resistance"], ambient_temperature=b["ambient_temperature"],
    )
    b["health_percent"] = result["battery_health_percent"]
    b["status"] = result["status"]
    b["factors"] = result["factors"]
    b["recommendations"] = result["recommendations"]

    m = state["motor"]
    m["temperature_c"] = clamp(m["temperature_c"] + rng.uniform(-2, 2), 35, 95)
    m["rpm"] = int(clamp(m["rpm"] + rng.uniform(-400, 400), 800, 8000))
    m["vibration_mm_s"] = round(clamp(m["vibration_mm_s"] + rng.uniform(-0.2, 0.2), 0.2, 6), 2)
    m["health_pct"] = clamp(m["health_pct"] + rng.uniform(-0.4, 0.2), 40, 100)

    br = state["brakes"]
    br["pad_wear_pct"] = clamp(br["pad_wear_pct"] + rng.uniform(0, 0.15), 0, 100)
    br["temperature_c"] = clamp(br["temperature_c"] + rng.uniform(-5, 5), 30, 220)

    env = state["environment"]
    env["temperature_c"] = clamp(env["temperature_c"] + rng.uniform(-0.8, 0.8), 15, 45)
    env["traffic_level"] = rng.choice(["Light", "Moderate", "Heavy"])

    tr = state["traffic"]
    tr["density_pct"] = clamp(tr["density_pct"] + rng.uniform(-6, 6), 10, 100)
    tr["congestion_score"] = clamp(tr["congestion_score"] + rng.uniform(-5, 5), 0, 100)

    # ---- Trip evolution (feeds Trip Information + hero panel live values) ----
    trip = state["trip"]
    traffic_speed_bands = {"Light": (45, 70), "Moderate": (22, 42), "Heavy": (8, 20)}
    lo, hi = traffic_speed_bands.get(env["traffic_level"], (25, 45))
    target_speed = rng.uniform(lo, hi)
    trip["current_speed_kmh"] = round(clamp(trip["current_speed_kmh"] + (target_speed - trip["current_speed_kmh"]) * 0.4, 0, 140), 1)
    trip["peak_speed_kmh"] = round(max(trip["peak_speed_kmh"], trip["current_speed_kmh"]), 1)

    tick_hours = 2.5 / 3600  # each tick represents ~2.5 simulated seconds
    if trip["current_speed_kmh"] < 3:
        trip["idle_time_min"] = round(trip["idle_time_min"] + tick_hours * 60, 2)
    else:
        distance_inc = trip["current_speed_kmh"] * tick_hours
        trip["distance_km"] = round(trip["distance_km"] + distance_inc, 2)
        energy_inc = distance_inc * (0.15 + (0 if b["state_of_charge"] > 20 else 0.02))
        trip["energy_used_kwh"] = round(trip["energy_used_kwh"] + energy_inc, 2)
        trip["energy_recovered_kwh"] = round(trip["energy_recovered_kwh"] + energy_inc * 0.18, 2)
    trip["duration_min"] = round(trip["duration_min"] + tick_hours * 60, 2)
    if trip["duration_min"] > 0:
        trip["avg_speed_kmh"] = round((trip["distance_km"] / (trip["duration_min"] / 60)) if trip["duration_min"] > 0 else 0, 1)
    remaining_km = max(0.0, 22.0 - trip["distance_km"])
    trip["eta_min"] = round((remaining_km / max(trip["avg_speed_kmh"], 15)) * 60, 1)

    # battery drains slightly as the trip consumes energy
    if trip["current_speed_kmh"] >= 3:
        b["state_of_charge"] = clamp(b["state_of_charge"] - rng.uniform(0.02, 0.08), 5, 100)

    state["last_analysis_time"] = datetime.now()

    # Append a new point to history, keep the last 30.
    h = state["history"]
    h["t"].append(datetime.now().strftime("%H:%M:%S"))
    h["battery_health"].append(b["health_percent"])
    h["motor_health"].append(round(m["health_pct"], 1))
    h["brake_wear"].append(round(br["pad_wear_pct"], 1))
    h["energy_consumption"].append(round(rng.uniform(12, 24), 1))
    h["driving_score"].append(round(state["driver"]["safety_score"] + rng.uniform(-3, 3), 1))
    h["efficiency"].append(round(rng.uniform(78, 95), 1))
    h["daily_distance"].append(round(rng.uniform(10, 60), 1))
    h["temperature"].append(env["temperature_c"])
    h["traffic_impact"].append(round(tr["density_pct"] / 8, 1))
    for key in h:
        if len(h[key]) > 30:
            h[key] = h[key][-30:]
    state["history"] = h

    _refresh_derived(state)


def _refresh_derived(state: dict):
    """Recomputes alerts and maintenance predictions from the latest raw state."""
    state["alerts"] = _generate_alerts(state)
    state["maintenance"] = _predict_maintenance(state)


def _generate_alerts(state: dict) -> list:
    """Rule-based alert generation from current thresholds across subsystems."""
    alerts = []
    b, m, br, tires = state["battery"], state["motor"], state["brakes"], state["tires"]

    if b["temperature"] > 42:
        alerts.append("Battery temperature slightly above optimal range.")
    if any(p < 30 for p in tires["pressure_psi"]):
        alerts.append("Rear-left tire pressure low.")
    if br["service_distance_km"] < 1000:
        alerts.append(f"Brake inspection due in {br['service_distance_km']} km.")
    if m["vibration_mm_s"] > 3.5:
        alerts.append("Motor vibration slightly increased.")
    if b["fast_charge_freq_per_week"] >= 5:
        alerts.append("Frequent fast charging detected this week.")
    if not alerts:
        alerts.append("No critical alerts. All monitored systems within normal range.")
    return alerts


def _predict_maintenance(state: dict) -> dict:
    """Builds the Predictive Maintenance table from all subsystem healths."""
    rng = random.Random(3)
    components = {
        "Battery": state["battery"]["health_percent"],
        "Motor": state["motor"]["health_pct"],
        "Brakes": 100 - state["brakes"]["pad_wear_pct"],
        "Suspension": state["suspension"]["shock_health_pct"],
        "Cooling System": clamp(90 - (state["motor"]["temperature_c"] - 50) * 0.5),
        "Steering": round(rng.uniform(75, 97), 1),
        "Tires": 100 - (sum(state["tires"]["wear_pct"]) / 4),
        "Inverter": round(rng.uniform(80, 98), 1),
        "Power Electronics": round(rng.uniform(82, 99), 1),
        "Charging Port": round(rng.uniform(85, 99), 1),
    }

    result = {}
    for name, health in components.items():
        health = round(clamp(health), 1)
        risk = round(clamp(100 - health + rng.uniform(-5, 5)), 1)
        remaining_life_days = int(max(10, health * 12 - rng.uniform(0, 100)))
        service_date = (datetime.now() + timedelta(days=remaining_life_days)).strftime("%d %b %Y")
        priority = "High" if health < 60 else ("Medium" if health < 80 else "Low")
        cost = int(rng.uniform(1500, 3000)) if priority == "High" else int(rng.uniform(500, 1500))
        recommendation = {
            "High": "Schedule service immediately",
            "Medium": "Plan service within the next month",
            "Low": "No action needed, continue monitoring",
        }[priority]

        result[name] = {
            "health": health,
            "failure_risk": risk,
            "remaining_life_days": remaining_life_days,
            "service_date": service_date,
            "priority": priority,
            "cost_estimate_inr": cost,
            "recommendation": recommendation,
        }
    return result
