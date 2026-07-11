"""
visualize_data.py
------------------
Generates exploratory data analysis (EDA) charts for the battery dataset
and saves them as PNG images in data/plots/. Understanding the data
visually before modeling helps catch bad synthetic-data assumptions and
confirms the relationships we intentionally built in (e.g. more cycles ->
lower health).

Run:
    python training/visualize_data.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend so this works without a display (headless servers).
import matplotlib.pyplot as plt
import seaborn as sns

# Allow importing from utils/ when running this script directly.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.data_processing import load_dataset, handle_missing_values, FEATURE_COLUMNS, TARGET_COLUMN

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "battery_data.csv")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "data", "plots")


def plot_health_distribution(df):
    """Histogram showing how Battery Health values are distributed."""
    plt.figure(figsize=(8, 5))
    sns.histplot(df[TARGET_COLUMN], bins=40, kde=True, color="steelblue")
    plt.title("Distribution of Battery Health (%)")
    plt.xlabel("Battery Health (%)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "health_distribution.png"), dpi=120)
    plt.close()


def plot_correlation_heatmap(df):
    """Heatmap showing how strongly each feature correlates with every other feature/target."""
    plt.figure(figsize=(9, 7))
    corr = df[FEATURE_COLUMNS + [TARGET_COLUMN]].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", square=True)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "correlation_heatmap.png"), dpi=120)
    plt.close()


def plot_scatter_relationships(df):
    """Scatter plots of the features most likely to drive Battery Health."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    sns.scatterplot(data=df, x="Charge_Discharge_Cycles", y=TARGET_COLUMN, alpha=0.3, ax=axes[0, 0], color="teal")
    axes[0, 0].set_title("Cycles vs Battery Health")

    sns.scatterplot(data=df, x="Battery_Age_Months", y=TARGET_COLUMN, alpha=0.3, ax=axes[0, 1], color="darkorange")
    axes[0, 1].set_title("Age vs Battery Health")

    sns.scatterplot(data=df, x="Battery_Temperature_C", y=TARGET_COLUMN, alpha=0.3, ax=axes[1, 0], color="firebrick")
    axes[1, 0].set_title("Temperature vs Battery Health")

    sns.scatterplot(data=df, x="Internal_Resistance_mOhm", y=TARGET_COLUMN, alpha=0.3, ax=axes[1, 1], color="purple")
    axes[1, 1].set_title("Internal Resistance vs Battery Health")

    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "scatter_relationships.png"), dpi=120)
    plt.close()


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)

    df = load_dataset(DATA_PATH)
    df = handle_missing_values(df)

    plot_health_distribution(df)
    plot_correlation_heatmap(df)
    plot_scatter_relationships(df)

    print(f"Saved 3 plots to: {os.path.abspath(PLOTS_DIR)}")
    print(" - health_distribution.png")
    print(" - correlation_heatmap.png")
    print(" - scatter_relationships.png")


if __name__ == "__main__":
    main()
