"""
predict.py
----------
Standalone inference script. This is intentionally decoupled from the
training/ folder: it only needs joblib + numpy + the saved model/scaler
files to run, which is exactly the lightweight footprint required for an
"Edge AI" deployment (no pandas, matplotlib, or sklearn training code
needed at inference time on the actual edge device, only sklearn's
predict-time dependency to unpickle/run the model).

Run interactively from the command line:
    python inference/predict.py

Or import and use programmatically (this is what the Streamlit app does):
    from inference.predict import BatteryHealthPredictor
    predictor = BatteryHealthPredictor()
    result = predictor.predict(voltage=380, temperature=32, ...)
"""

import os
import sys

import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.data_processing import FEATURE_COLUMNS
from utils.explainability import generate_explanation

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "battery_health_model.joblib")
SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "scaler.joblib")


class BatteryHealthPredictor:
    """
    Wraps the saved model + scaler and exposes a simple `.predict()`
    method. Loading happens once in __init__ so repeated predictions
    (e.g. from a dashboard) don't reload the model from disk every time.
    """

    def __init__(self, model_path: str = MODEL_PATH, scaler_path: str = SCALER_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run training/train_model.py first."
            )
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

    def predict(
        self,
        voltage: float,
        temperature: float,
        state_of_charge: float,
        charge_cycles: float,
        current: float,
        battery_age_months: float,
        internal_resistance: float = 45.0,
        ambient_temperature: float = 28.0,
    ) -> dict:
        """
        Predicts battery health and returns a full explainable result.

        Parameters correspond to the 8 features the model was trained on.
        `internal_resistance` and `ambient_temperature` are optional per
        the project spec and default to typical/neutral values if the
        user doesn't have sensors for them.

        Returns
        -------
        dict
            {
                "battery_health_percent": float,
                "status": str,
                "factors": list[str],
                "recommendations": list[str],
            }
        """
        # Build the feature vector in the EXACT order the model expects.
        # Using FEATURE_COLUMNS (shared with training) guarantees this
        # order always matches what the scaler/model were fit on.
        raw_inputs = {
            "Battery_Voltage_V": voltage,
            "Battery_Temperature_C": temperature,
            "State_of_Charge_Percent": state_of_charge,
            "Charge_Discharge_Cycles": charge_cycles,
            "Current_A": current,
            "Battery_Age_Months": battery_age_months,
            "Internal_Resistance_mOhm": internal_resistance,
            "Ambient_Temperature_C": ambient_temperature,
        }

        # Building a one-row DataFrame (not a raw numpy array) keeps the
        # column names attached, which avoids sklearn's "X does not have
        # valid feature names" warning since the scaler was fit on a
        # DataFrame with these same column names during training.
        feature_frame = pd.DataFrame([raw_inputs])[FEATURE_COLUMNS]
        scaled_vector = self.scaler.transform(feature_frame)

        predicted_health = float(self.model.predict(scaled_vector)[0])
        predicted_health = round(min(max(predicted_health, 0), 100), 2)  # clamp to sane range

        explanation = generate_explanation(raw_inputs, predicted_health)

        return {
            "battery_health_percent": predicted_health,
            "status": explanation["status"],
            "factors": explanation["factors"],
            "recommendations": explanation["recommendations"],
        }


def run_cli():
    """Interactive command-line prediction tool."""
    print("=== Edge AI Battery Health Prediction ===\n")

    try:
        predictor = BatteryHealthPredictor()
    except FileNotFoundError as e:
        print(str(e))
        return

    def ask_float(prompt):
        while True:
            try:
                return float(input(prompt))
            except ValueError:
                print("Please enter a valid number.")

    voltage = ask_float("Battery Voltage (V): ")
    temperature = ask_float("Battery Temperature (C): ")
    soc = ask_float("State of Charge (%): ")
    cycles = ask_float("Charge/Discharge Cycles: ")
    current = ask_float("Current (A, negative = discharging): ")
    age = ask_float("Battery Age (months): ")

    result = predictor.predict(
        voltage=voltage,
        temperature=temperature,
        state_of_charge=soc,
        charge_cycles=cycles,
        current=current,
        battery_age_months=age,
    )

    print("\n--- Prediction Result ---")
    print(f"Battery Health: {result['battery_health_percent']}%")
    print(f"Status: {result['status']}")
    print("\nPossible contributing factors:")
    for factor in result["factors"]:
        print(f"  - {factor}")
    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  - {rec}")


if __name__ == "__main__":
    run_cli()
