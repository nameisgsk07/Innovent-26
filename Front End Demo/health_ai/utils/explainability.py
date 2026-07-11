"""
explainability.py
------------------
Rule-based classification and explanation logic, shared by both the CLI
inference script and the Streamlit dashboard so their outputs always
agree. This is a simple, transparent alternative to a full explainable-AI
framework (e.g. SHAP) - good enough as a first version and easy to
upgrade later without touching the rest of the app.
"""

# Configurable thresholds for battery status classification.
# Kept as named constants (not magic numbers) so they're easy to tune.
HEALTH_THRESHOLD_GOOD = 80.0     # >= this value => "Good"
HEALTH_THRESHOLD_WARNING = 65.0  # >= this value (but < GOOD) => "Warning"
# below HEALTH_THRESHOLD_WARNING => "Replace Soon"

# Thresholds used to decide whether an input feature is "contributing" to
# degraded health, based on the physical relationships built into the
# synthetic dataset (utils/generate_data.py).
TEMP_HIGH_THRESHOLD_C = 40.0
CYCLES_HIGH_THRESHOLD = 1500
AGE_HIGH_THRESHOLD_MONTHS = 60
RESISTANCE_HIGH_THRESHOLD_MOHM = 70


def classify_battery_status(health_percent: float) -> str:
    """
    Classifies battery health percentage into a human-readable status.

    Parameters
    ----------
    health_percent : float
        Predicted battery health (0-100).

    Returns
    -------
    str
        One of "Good", "Warning", "Replace Soon".
    """
    if health_percent >= HEALTH_THRESHOLD_GOOD:
        return "Good"
    elif health_percent >= HEALTH_THRESHOLD_WARNING:
        return "Warning"
    else:
        return "Replace Soon"


def generate_explanation(inputs: dict, health_percent: float) -> dict:
    """
    Generates a simple rule-based explanation of the predicted battery
    health, listing contributing factors and recommendations.

    Parameters
    ----------
    inputs : dict
        Raw input values, keyed by feature name, e.g.:
        {
            "Battery_Voltage_V": ...,
            "Battery_Temperature_C": ...,
            "State_of_Charge_Percent": ...,
            "Charge_Discharge_Cycles": ...,
            "Current_A": ...,
            "Battery_Age_Months": ...,
            "Internal_Resistance_mOhm": ...,   (optional)
            "Ambient_Temperature_C": ...,       (optional)
        }
    health_percent : float
        The model's predicted battery health.

    Returns
    -------
    dict
        {
            "status": str,
            "factors": list[str],
            "recommendations": list[str],
        }
    """
    factors = []
    recommendations = []

    temperature = inputs.get("Battery_Temperature_C")
    cycles = inputs.get("Charge_Discharge_Cycles")
    age = inputs.get("Battery_Age_Months")
    resistance = inputs.get("Internal_Resistance_mOhm")

    if temperature is not None and temperature > TEMP_HIGH_THRESHOLD_C:
        factors.append("High operating temperature")
        recommendations.append("Avoid frequent fast charging and park in shaded/cooler areas")

    if cycles is not None and cycles > CYCLES_HIGH_THRESHOLD:
        factors.append("High number of charge/discharge cycles")
        recommendations.append("Reduce full charge/discharge cycles; prefer partial charging (20-80%)")

    if age is not None and age > AGE_HIGH_THRESHOLD_MONTHS:
        factors.append("Moderate to significant battery aging")
        recommendations.append("Schedule a professional battery inspection")

    if resistance is not None and resistance > RESISTANCE_HIGH_THRESHOLD_MOHM:
        factors.append("Elevated internal resistance")
        recommendations.append("Monitor charging efficiency; internal resistance rise often precedes failure")

    # If nothing crossed a threshold but health still isn't great, give a
    # generic factor/recommendation so the explanation is never empty.
    if not factors:
        if health_percent < HEALTH_THRESHOLD_GOOD:
            factors.append("Combined mild wear across multiple parameters")
            recommendations.append("Continue normal usage and monitor health trend over time")
        else:
            factors.append("No significant risk factors detected")
            recommendations.append("Maintain current usage and charging habits")

    status = classify_battery_status(health_percent)

    return {
        "status": status,
        "factors": factors,
        "recommendations": recommendations,
    }
