"""
train_model.py
---------------
Trains a Random Forest Regressor to predict Battery Health (%) from
battery operating parameters, evaluates it, and saves the trained model
and scaler to disk for later use by the inference/ and app/ modules.

WHY Random Forest for this problem?
------------------------------------
1. Tabular, moderate-sized data: Random Forests are a strong default for
   structured/tabular sensor data like this (a handful of numeric
   features, no images/text), often matching or beating more complex
   models without heavy tuning.
2. Non-linear relationships: Battery health depends on non-linear and
   interacting effects (e.g. temperature damage accelerates *combined*
   with high cycle count). Tree ensembles capture such interactions
   naturally, unlike plain linear regression.
3. Robust to outliers/noise: Individual decision trees can overfit, but
   averaging many trees (bagging) smooths this out, which suits our
   dataset that includes injected sensor noise and missing-value fills.
4. Built-in feature importance: Random Forests expose
   `feature_importances_`, which is exactly what the project needs for
   the "Feature Importance" chart and explainable output - no extra
   library required.
5. Fast, edge-friendly, and interpretable enough to be a strong,
   easy-to-explain FIRST model, matching the project's request to
   "begin with a traditional ML model."

Run:
    python training/train_model.py
Outputs:
    models/battery_health_model.joblib
    models/scaler.joblib
    models/feature_importance.png
"""

import os
import sys

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.data_processing import (
    load_dataset,
    handle_missing_values,
    select_features_and_target,
    split_and_scale,
    FEATURE_COLUMNS,
)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "battery_data.csv")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


def train_random_forest(X_train, y_train) -> RandomForestRegressor:
    """
    Trains a Random Forest Regressor on the given training data.

    Parameters
    ----------
    X_train : array-like
        Scaled training features.
    y_train : array-like
        Training targets (Battery Health %).

    Returns
    -------
    RandomForestRegressor
        The fitted model.
    """
    model = RandomForestRegressor(
        n_estimators=300,      # number of trees - more trees = more stable predictions
        max_depth=14,          # limits tree depth to reduce overfitting
        min_samples_leaf=4,    # requires at least 4 samples per leaf, smooths predictions
        random_state=42,
        n_jobs=-1,             # use all available CPU cores for faster training
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    """
    Evaluates the trained model on the held-out test set and prints
    MAE, RMSE, and R^2, as required by the project spec.

    Parameters
    ----------
    model : RandomForestRegressor
        The trained model.
    X_test : array-like
        Scaled test features.
    y_test : array-like
        True test targets.

    Returns
    -------
    dict
        Dictionary of the computed metrics.
    """
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    print("\n--- Model Evaluation ---")
    print(f"MAE  (Mean Absolute Error):      {mae:.3f} %")
    print(f"RMSE (Root Mean Squared Error):  {rmse:.3f} %")
    print(f"R^2  (Coefficient of Determination): {r2:.4f}")

    return {"mae": mae, "rmse": rmse, "r2": r2}


def plot_feature_importance(model, feature_names):
    """
    Plots and saves a horizontal bar chart of feature importances, sorted
    from most to least important. This is also reused by the dashboard.
    """
    importances = model.feature_importances_
    order = np.argsort(importances)  # ascending, so barh reads top-to-bottom as most-important

    plt.figure(figsize=(8, 6))
    plt.barh(np.array(feature_names)[order], importances[order], color="seagreen")
    plt.xlabel("Importance")
    plt.title("Feature Importance - Battery Health Prediction")
    plt.tight_layout()
    plt.savefig(os.path.join(MODELS_DIR, "feature_importance.png"), dpi=120)
    plt.close()


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1. Load and clean data
    df = load_dataset(DATA_PATH)
    df = handle_missing_values(df)

    # 2. Select features/target and split+scale
    X, y = select_features_and_target(df)
    X_train, X_test, y_train, y_test, scaler = split_and_scale(X, y)

    # 3. Train
    print("Training Random Forest Regressor...")
    model = train_random_forest(X_train, y_train)

    # 4. Evaluate
    metrics = evaluate_model(model, X_test, y_test)

    # 5. Feature importance chart
    plot_feature_importance(model, FEATURE_COLUMNS)
    print(f"\nSaved feature importance chart to: {os.path.join(MODELS_DIR, 'feature_importance.png')}")

    # 6. Save model + scaler for inference/app to reuse
    model_path = os.path.join(MODELS_DIR, "battery_health_model.joblib")
    scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\nSaved trained model to: {model_path}")
    print(f"Saved scaler to: {scaler_path}")

    return metrics


if __name__ == "__main__":
    main()
