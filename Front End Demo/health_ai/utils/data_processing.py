"""
data_processing.py
-------------------
Shared data utilities used by both the training pipeline and (optionally)
future retraining jobs. Kept in utils/ so training and any future scripts
can reuse the exact same cleaning/scaling logic - this avoids "training
skew" where training and inference process data differently.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# The feature columns the model is trained on, in a fixed order. Keeping
# this list in one place means training and inference always agree on
# which columns matter and in what order they're fed to the model.
FEATURE_COLUMNS = [
    "Battery_Voltage_V",
    "Battery_Temperature_C",
    "State_of_Charge_Percent",
    "Charge_Discharge_Cycles",
    "Current_A",
    "Battery_Age_Months",
    "Internal_Resistance_mOhm",
    "Ambient_Temperature_C",
]

TARGET_COLUMN = "Battery_Health_Percent"


def load_dataset(csv_path: str) -> pd.DataFrame:
    """
    Loads the battery dataset from a CSV file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        The raw, unprocessed dataset.
    """
    df = pd.read_csv(csv_path)
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fills missing sensor readings using the column median.

    We use the median (not mean) because it is robust to outliers - a
    single extreme sensor glitch won't skew the fill value as much as it
    would with a mean.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset that may contain NaN values.

    Returns
    -------
    pd.DataFrame
        Dataset with missing values filled.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].isnull().sum() > 0:
            median_value = df[col].median()
            df[col] = df[col].fillna(median_value)
    return df


def select_features_and_target(df: pd.DataFrame):
    """
    Splits the dataframe into the feature matrix X and target vector y.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned dataset.

    Returns
    -------
    tuple(pd.DataFrame, pd.Series)
        X (features) and y (target: Battery_Health_Percent).
    """
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y


def split_and_scale(X, y, test_size: float = 0.2, random_state: int = 42):
    """
    Splits data into train/test sets and scales features using
    StandardScaler (zero mean, unit variance).

    Note: Random Forests don't strictly require feature scaling to work
    correctly (they split on thresholds, not distances), but we scale
    anyway so the pipeline is ready to plug in scale-sensitive models
    later (e.g. neural networks, SVR) without changing this function.

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix.
    y : pd.Series
        Target vector.
    test_size : float
        Fraction of data reserved for testing.
    random_state : int
        Seed for reproducibility.

    Returns
    -------
    tuple
        X_train_scaled, X_test_scaled, y_train, y_test, fitted_scaler
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    scaler = StandardScaler()
    # Fit ONLY on training data to avoid data leakage from the test set.
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler
