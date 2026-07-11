"""
export_onnx.py
---------------
Exports the trained scikit-learn Random Forest model to the ONNX format.

WHY ONNX for Edge AI?
----------------------
ONNX (Open Neural Network Exchange) is a hardware/framework-agnostic model
format. Once exported:
  - The model can run via `onnxruntime`, a lightweight C++ runtime with
    bindings for Python, C++, Java, C#, and JavaScript - without needing
    scikit-learn installed on the edge device at all.
  - It can be deployed to resource-constrained hardware (e.g. Raspberry Pi,
    microcontrollers with onnxruntime support, mobile devices) far more
    easily than shipping a full Python + scikit-learn environment.
  - Inference is typically faster than the original scikit-learn model
    because ONNX Runtime applies graph-level optimizations.

This script is intentionally separate from train_model.py: exporting is
an optional "packaging" step for deployment, not a required part of
training/evaluating the model.

Run:
    python training/export_onnx.py
Output:
    models/battery_health_model.onnx
"""

import os

import joblib
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "battery_health_model.joblib")
ONNX_PATH = os.path.join(PROJECT_ROOT, "models", "battery_health_model.onnx")


def export_model_to_onnx():
    """Loads the saved joblib model and converts it to ONNX format."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run training/train_model.py first."
        )

    model = joblib.load(MODEL_PATH)

    # The model expects 8 input features (see utils.data_processing.FEATURE_COLUMNS).
    # `None` for the batch dimension means the exported model accepts any
    # number of rows at inference time, not just a single sample.
    num_features = 8
    initial_type = [("float_input", FloatTensorType([None, num_features]))]

    onnx_model = convert_sklearn(model, initial_types=initial_type)

    with open(ONNX_PATH, "wb") as f:
        f.write(onnx_model.SerializeToString())

    print(f"Exported ONNX model to: {ONNX_PATH}")
    return ONNX_PATH


def verify_onnx_model(sample_input: np.ndarray):
    """
    Sanity check: runs the exported ONNX model with onnxruntime and prints
    the output, confirming the export produces a working, loadable model.
    """
    import onnxruntime as rt

    session = rt.InferenceSession(ONNX_PATH)
    input_name = session.get_inputs()[0].name
    output = session.run(None, {input_name: sample_input.astype(np.float32)})
    print(f"ONNX model verification prediction: {output[0]}")


if __name__ == "__main__":
    export_model_to_onnx()

    # Verify with a dummy scaled input (8 features, 1 sample).
    dummy_input = np.zeros((1, 8), dtype=np.float32)
    verify_onnx_model(dummy_input)
