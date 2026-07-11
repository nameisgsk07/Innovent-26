"""
generate_data.py
-----------------
Generates a SYNTHETIC but physically-plausible electric-vehicle battery
dataset. Real battery degradation depends on a combination of factors:
cycling (wear from repeated charge/discharge), heat (accelerates chemical
aging), depth of discharge, current stress, and calendar aging (age in
days/months regardless of use).

Instead of pure random noise, we build "Battery Health" from a formula
that mimics these known relationships, then add small random noise so the
dataset still requires a model to learn (not a plain lookup formula).

Run:
    python training/generate_data.py
Output:
    data/battery_data.csv
"""

import numpy as np
import pandas as pd
import os

# Fixing the random seed makes the dataset reproducible - anyone who runs
# this script gets the exact same data, which is important for debugging.
np.random.seed(42)

# Number of samples to generate. The project spec requires at least 10,000.
NUM_SAMPLES = 12000


def generate_battery_dataset(num_samples: int = NUM_SAMPLES) -> pd.DataFrame:
    """
    Generates a synthetic dataset of EV battery operating parameters and
    a computed Battery Health (%) target.

    Parameters
    ----------
    num_samples : int
        Number of rows (battery "snapshots") to generate.

    Returns
    -------
    pd.DataFrame
        The generated dataset with feature columns and the target column
        'Battery_Health_Percent'.
    """

    # ---- 1. Simulate raw operating parameters ----

    # Battery age in months. Uniform between a brand-new pack (0) and an
    # aged pack (96 months = 8 years), which is realistic for EV packs.
    battery_age_months = np.random.uniform(0, 96, num_samples)

    # Charge/discharge cycle count. Cycle count generally correlates with
    # age (older batteries have been cycled more) but with variation since
    # usage patterns differ between drivers. We derive cycles partly from
    # age plus random usage intensity, rather than making it independent.
    usage_intensity = np.random.uniform(0.5, 1.5, num_samples)  # driver behavior factor
    charge_cycles = (battery_age_months * 30 * usage_intensity * 0.3) + np.random.normal(0, 50, num_samples)
    charge_cycles = np.clip(charge_cycles, 0, 4000)

    # State of Charge (SoC) at the time of the reading, in %.
    state_of_charge = np.random.uniform(5, 100, num_samples)

    # Battery voltage. A healthy EV pack nominal voltage is modeled around
    # 350-400V (typical for many EV packs), and it naturally sags a bit at
    # low SoC and rises toward full SoC.
    base_voltage = 350 + (state_of_charge / 100) * 50
    battery_voltage = base_voltage + np.random.normal(0, 3, num_samples)

    # Current draw in Amps. Negative = discharging, positive = charging.
    # We simulate mostly discharge behavior (driving) with occasional charging.
    current = np.random.normal(-40, 60, num_samples)

    # Ambient temperature (deg C) - environmental temperature the car sits/drives in.
    ambient_temperature = np.random.normal(28, 10, num_samples)
    ambient_temperature = np.clip(ambient_temperature, -10, 50)

    # Battery temperature is influenced by ambient temperature PLUS heat
    # generated internally from current draw (I^2R heating), which is why
    # we add a term proportional to the square of the current.
    battery_temperature = (
        ambient_temperature
        + 0.002 * (current ** 2)
        + np.random.normal(0, 2, num_samples)
    )
    battery_temperature = np.clip(battery_temperature, -10, 70)

    # Internal resistance (milliohms). This is one of the strongest real
    # indicators of battery aging - resistance grows as the battery ages
    # and as cycle count increases (electrode degradation, SEI layer growth).
    internal_resistance = (
        30
        + (battery_age_months * 0.15)
        + (charge_cycles * 0.01)
        + np.random.normal(0, 2, num_samples)
    )
    internal_resistance = np.clip(internal_resistance, 20, 150)

    # ---- 2. Compute Battery Health (%) from the above factors ----
    # This formula encodes realistic degradation knowledge:
    #   - More cycles -> lower health (cycle fatigue)
    #   - Higher age -> lower health (calendar aging)
    #   - Higher average operating temperature -> lower health (heat stress)
    #   - Higher internal resistance -> lower health (direct aging indicator)
    # Weights are chosen so that a brand-new, lightly used, cool-running
    # battery scores near 100%, and a heavily cycled, hot, old, high
    # resistance battery scores near 50-60%.

    health = (
        100
        - (charge_cycles * 0.008)            # cycle wear
        - (battery_age_months * 0.12)         # calendar aging
        - np.maximum(0, battery_temperature - 30) * 0.25  # heat stress above 30C
        - (internal_resistance - 30) * 0.15   # resistance-driven aging
    )

    # Add small random measurement/manufacturing noise so the relationship
    # is realistic (not a perfect deterministic formula) and clip to a
    # believable battery health range.
    health += np.random.normal(0, 2, num_samples)
    health = np.clip(health, 40, 100)

    # ---- 3. Assemble the DataFrame ----
    df = pd.DataFrame({
        "Battery_Voltage_V": battery_voltage.round(2),
        "Battery_Temperature_C": battery_temperature.round(2),
        "State_of_Charge_Percent": state_of_charge.round(2),
        "Charge_Discharge_Cycles": charge_cycles.round(0).astype(int),
        "Current_A": current.round(2),
        "Battery_Age_Months": battery_age_months.round(1),
        "Internal_Resistance_mOhm": internal_resistance.round(2),
        "Ambient_Temperature_C": ambient_temperature.round(2),
        "Battery_Health_Percent": health.round(2),
    })

    # ---- 4. Inject a small amount of missing data ----
    # Real-world sensor data almost always has some missing readings
    # (sensor dropout, transmission errors). We deliberately inject ~1%
    # missing values into a couple of columns so the data-processing step
    # (handling missing values) has something real to do.
    for col in ["Battery_Temperature_C", "Internal_Resistance_mOhm"]:
        missing_idx = np.random.choice(df.index, size=int(0.01 * len(df)), replace=False)
        df.loc[missing_idx, col] = np.nan

    return df


def main():
    """Generates the dataset and saves it to data/battery_data.csv."""
    df = generate_battery_dataset()

    # Ensure the data/ folder exists relative to the project root.
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "battery_data.csv")

    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} samples.")
    print(f"Saved dataset to: {os.path.abspath(output_path)}")
    print("\nPreview:")
    print(df.head())
    print("\nSummary statistics:")
    print(df.describe())


if __name__ == "__main__":
    main()
