# Edge AI Vehicle Intelligence Platform
### (built on top of the Battery Health Prediction System)

An offline, edge-deployable AI platform that started as a battery health
predictor and has been expanded into a full **Vehicle Intelligence
Platform**: battery, motor, brakes, tires, suspension, driver behaviour,
daily driving patterns, environment, traffic, ADAS, predictive
maintenance, and charging intelligence — all in one dashboard.

**Important note on data:** the battery numbers come from the real
trained Random Forest model (see below). Every other subsystem (motor,
brakes, tires, suspension, driver behaviour, environment, traffic, ADAS,
predictive maintenance) is **realistic simulated data**, generated in
`utils/vehicle_simulation.py`, since real telemetry for those systems
isn't available here. This is a technology demonstration, not a
production vehicle diagnostic tool.

Launch the full platform with:
```bash
streamlit run app/dashboard.py
```
Toggle **Demo Mode** in the sidebar for a live, auto-updating simulation
suitable for presentations.

---


## 1. Project Overview

The system is built around a **Random Forest Regressor** trained on a
realistic **synthetic dataset** (12,000 samples) that encodes known
battery-degradation physics: cycle fatigue, calendar aging, heat stress,
and internal resistance growth. On top of the model sit:

- A **rule-based explainability layer** that turns a raw percentage into
  human-readable contributing factors and recommendations.
- A **Streamlit dashboard** for interactive local use.
- An **ONNX export path** so the trained model can be deployed to
  lightweight/edge runtimes without needing scikit-learn installed.

Current model performance (Random Forest, held-out test set):

| Metric | Value |
|---|---|
| MAE  | ~1.64% |
| RMSE | ~2.07% |
| R²   | ~0.917 |

---

## 2. Folder Structure

```
battery_health_ai/
├── data/
│   ├── battery_data.csv          # generated synthetic dataset
│   └── plots/                    # EDA charts (distribution, correlation, scatter)
├── models/
│   ├── battery_health_model.joblib   # trained Random Forest model
│   ├── scaler.joblib                 # fitted StandardScaler
│   ├── battery_health_model.onnx     # ONNX-exported model (edge deployment)
│   └── feature_importance.png        # feature importance chart
├── training/
│   ├── generate_data.py          # synthetic dataset generator
│   ├── visualize_data.py         # EDA chart generation
│   ├── train_model.py            # trains, evaluates, saves the model
│   └── export_onnx.py            # exports the model to ONNX
├── inference/
│   └── predict.py                # standalone, lightweight prediction script
├── app/
│   └── dashboard.py               # Edge AI Vehicle Intelligence Platform (Streamlit, multi-tab)
├── utils/
│   ├── data_processing.py        # shared load/clean/scale functions
│   ├── explainability.py         # battery status classification + rule-based explanations
│   ├── vehicle_simulation.py     # synthetic state generator for every subsystem + live "tick"
│   ├── ai_engine.py              # cross-system AI recommendations, explanations, assistant Q&A
│   └── ui_components.py          # dark theme CSS, gauges, radar charts, metric cards
├── notebooks/                    # optional space for exploratory analysis
├── requirements.txt
└── README.md
```

**Design principle:** `training/` and `inference/` are kept separate on
purpose. `inference/predict.py` only needs `joblib`, `numpy`, and
`pandas` plus the saved model files — it does not import scikit-learn's
training utilities, matplotlib, or seaborn, keeping it lightweight enough
to run on constrained edge hardware alongside the ONNX runtime.

---

## 3. Installation

Requires Python 3.9+.

```bash
cd battery_health_ai
pip install -r requirements.txt
```

---

## 4. How to Generate the Dataset

```bash
python training/generate_data.py
```

This creates `data/battery_data.csv` with 12,000 samples. The generator
does **not** use pure randomness for the target — Battery Health is
computed from a formula combining cycle count, age, temperature stress,
and internal resistance, then given light random noise, so the dataset
mimics real degradation behavior.

To view the EDA charts (distribution, correlation heatmap, scatter plots):

```bash
python training/visualize_data.py
```

Charts are saved to `data/plots/`.

---

## 5. How to Train the Model

```bash
python training/train_model.py
```

This will:
1. Load and clean `data/battery_data.csv` (median-fills missing sensor values).
2. Split into train/test sets and scale features.
3. Train a `RandomForestRegressor` (300 trees, max depth 14).
4. Print MAE, RMSE, and R² on the test set.
5. Save the feature importance chart to `models/feature_importance.png`.
6. Save the trained model and scaler to `models/`.

### Why Random Forest?
Battery health depends on non-linear, interacting factors (e.g., heat
damage compounds with high cycle count). Random Forests handle these
interactions naturally, are robust to noisy/missing sensor data, need
little tuning, and expose `feature_importances_` out of the box — making
them a strong, interpretable first model for this tabular problem.

---

## 6. How to Run Predictions (Command Line)

```bash
python inference/predict.py
```

You'll be prompted for voltage, temperature, SoC, cycles, current, and
age. The script prints the predicted Battery Health %, a status
(**Good / Warning / Replace Soon**), contributing factors, and
recommendations.

You can also use it programmatically:

```python
from inference.predict import BatteryHealthPredictor

predictor = BatteryHealthPredictor()
result = predictor.predict(
    voltage=375, temperature=32, state_of_charge=55,
    charge_cycles=800, current=-40, battery_age_months=24,
)
print(result)
```

### Status Thresholds (configurable in `utils/explainability.py`)
| Health % | Status |
|---|---|
| ≥ 80% | Good |
| 65% – 79.9% | Warning |
| < 65% | Replace Soon |

---

## 7. How to Launch the Dashboard

```bash
streamlit run app/dashboard.py
```

The app opens in **Driver View** by default — a Tesla/Rivian-style
infotainment layout with a "Liquid Glass"-inspired premium theme (frosted
glass panels, soft blur, floating shadows, a subtle ambient background
shimmer). The home screen deliberately answers only four questions — is
the vehicle healthy, how much battery/range is left, what to know before
driving, and whether anything needs attention — via an AI greeting, a
friendly mood indicator (🟢/🟡/🔴), a natural-language AI summary,
animated battery/trip/range numbers, and a floating AI companion that
rotates short insights on its own timer. Everything more detailed
(charging, drive intelligence, ADAS-style features, comfort, an AI
vehicle-care inspection, settings) lives behind the left navigation rail.
Use the **Insights View** button at the top to switch to the original
multi-tab technical dashboard (Battery Intelligence, Motor & Chassis,
ADAS, Predictive Maintenance, etc.) — both views read the same
underlying simulated vehicle state, so they always agree with each
other.

The dashboard provides:
- Sliders for all input parameters (voltage, temperature, SoC, cycles,
  current, age, plus optional internal resistance / ambient temperature).
- A gauge showing predicted Battery Health.
- Status badge (Good / Warning / Replace Soon) with contributing factors
  and recommendations.
- A feature importance chart.
- A running history chart of predictions made during the session.

---

## 8. Exporting to ONNX (Edge Deployment)

```bash
python training/export_onnx.py
```

Produces `models/battery_health_model.onnx` and verifies it loads
correctly with `onnxruntime`. This ONNX file can be deployed to edge
runtimes (mobile, embedded Linux boards, browsers via `onnxruntime-web`,
etc.) without needing scikit-learn on the target device.

---

## 9. Offline / Edge AI Notes

- No network calls are made anywhere in `training/`, `inference/`, or `app/`.
- `inference/predict.py` has a minimal dependency footprint by design.
- The ONNX export path decouples the deployed model from the Python/
  scikit-learn training environment entirely.

---

## 10. Future Improvements

- Replace the rule-based explanation layer with SHAP values for
  quantitative, per-prediction feature attribution.
- Add a Gradient Boosting / XGBoost model as a comparison baseline.
- Incorporate real EV telemetry data once available, replacing/augmenting
  the synthetic dataset.
- Add automated retraining triggered by new data drops into `data/`.
- Persist dashboard prediction history to disk (currently session-only).
- Add unit tests for `utils/data_processing.py` and `utils/explainability.py`.
- Extend the modular structure with additional vehicle-health modules
  (e.g., motor health, brake wear) alongside battery health.
