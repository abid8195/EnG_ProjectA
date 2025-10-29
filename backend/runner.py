# backend/runner.py
from typing import Dict, Any
import os
import numpy as np
import pandas as pd

# ---------------- Robust Qiskit imports (algorithm_globals supports both locations) ----------------
try:
    from qiskit_algorithms.utils import algorithm_globals  # preferred in newer installs
except Exception:
    from qiskit.utils import algorithm_globals  # legacy location

from qiskit.primitives import Estimator
try:
    from qiskit.algorithms.optimizers import COBYLA  # qiskit>=0.46 style
except Exception:
    from qiskit_algorithms.optimizers import COBYLA  # fallback

from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.algorithms.classifiers import NeuralNetworkClassifier
from qiskit.circuit.library import ZZFeatureMap, RealAmplitudes

# ---------------- scikit-learn utilities ----------------
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


def _validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    required_paths = [
        ("pipeline", None),
        ("qnn.type", None),
        ("dataset.type", None),
        ("dataset.path", None),
        ("dataset.label_column", None),
        ("dataset.feature_columns", None),
        ("circuit.num_qubits", None),
        ("circuit.reps", None),
        ("optimizer.type", None),
        ("optimizer.maxiter", None),
    ]

    def _get(d: Dict[str, Any], dotted: str):
        cur = d
        for key in dotted.split("."):
            if not isinstance(cur, dict) or key not in cur:
                return None
            cur = cur[key]
        return cur

    missing = [p for p, _ in required_paths if _get(spec, p) is None]
    if missing:
        return {"error": f"Missing required spec keys: {missing}", "received_spec": spec}
    if spec.get("pipeline") != "qml-classifier":
        return {"error": "pipeline must be 'qml-classifier'", "received_spec": spec}
    if spec.get("qnn", {}).get("type") != "estimator":
        return {"error": "qnn.type must be 'estimator'", "received_spec": spec}
    if spec.get("dataset", {}).get("type") != "csv":
        return {"error": "dataset.type must be 'csv'", "received_spec": spec}
    if spec.get("optimizer", {}).get("type", "").lower() != "cobyla":
        return {"error": "optimizer.type must be 'cobyla'", "received_spec": spec}
    return {}


def _resolve_csv_path(csv_path: str) -> str:
    if os.path.isabs(csv_path):
        return csv_path
    here = os.path.dirname(__file__)
    candidate1 = os.path.join(here, csv_path)
    if os.path.exists(candidate1):
        return candidate1
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    candidate2 = os.path.join(project_root, csv_path)
    return candidate2


def _load_and_prepare_data(ds: Dict[str, Any], target_dimension: int, seed: int):
    algorithm_globals.random_seed = seed

    path = ds.get("path")
    label_col = ds.get("label_column")
    feat_cols = ds.get("feature_columns") or []
    test_size = float(ds.get("test_size", 0.2))
    shuffle = bool(ds.get("shuffle", True))

    if not path or not label_col or not feat_cols:
        raise ValueError("dataset.path, dataset.label_column, and dataset.feature_columns are required")

    csv_path = _resolve_csv_path(path)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV appears to be empty")
    for c in [label_col, *feat_cols]:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found in CSV headers: {df.columns.tolist()}")

    X_raw = df[feat_cols].to_numpy()
    y_raw = df[label_col].to_numpy()

    # Multiclass -> pick two most frequent classes (one-vs-one simplification)
    unique, counts = np.unique(y_raw, return_counts=True)
    if len(unique) > 2:
        order = np.argsort(counts)[::-1]
        keep = set(unique[order][:2])
        mask = np.isin(y_raw, list(keep))
        X_raw = X_raw[mask]
        y_raw = y_raw[mask]

    # Map labels to {-1, +1}
    classes = np.unique(y_raw)
    if len(classes) != 2:
        raise ValueError(f"After filtering, need exactly 2 classes, got {classes.tolist()}")
    major = classes[0]
    if np.sum(y_raw == classes[1]) > np.sum(y_raw == classes[0]):
        major = classes[1]
    y_bin = np.where(y_raw == major, 1, -1)

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y_bin, test_size=test_size, shuffle=shuffle, random_state=seed
    )

    # Preprocess: impute (median), scale, PCA to target_dimension
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    pca = PCA(n_components=target_dimension, random_state=seed)

    X_train_imp = imputer.fit_transform(X_train_raw)
    X_test_imp = imputer.transform(X_test_raw)

    X_train_scl = scaler.fit_transform(X_train_imp)
    X_test_scl = scaler.transform(X_test_imp)

    # If features < target_dimension, PCA will fail; handle by padding
    if X_train_scl.shape[1] >= target_dimension:
        X_train = pca.fit_transform(X_train_scl)
        X_test = pca.transform(X_test_scl)
    else:
        # Pad with zeros to reach target_dimension
        def _pad(X):
            if X.shape[1] == target_dimension:
                return X
            pad = target_dimension - X.shape[1]
            return np.hstack([X, np.zeros((X.shape[0], pad))])
        X_train = _pad(X_train_scl)
        X_test = _pad(X_test_scl)

    shapes = {
        "X_train": list(X_train.shape),
        "X_test": list(X_test.shape),
    }

    preprocessors = {
        "imputer": imputer,
        "scaler": scaler,
        "pca": pca,
    }

    return X_train, X_test, y_train, y_test, shapes, preprocessors


def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
    # Validate spec
    err = _validate_spec(spec or {})
    if err:
        return err

    # Seed for determinism
    algorithm_globals.random_seed = 42

    ds = spec.get("dataset", {})
    circ = spec.get("circuit", {})
    opt = spec.get("optimizer", {})
    outputs = spec.get("outputs", {})

    num_qubits = int(circ.get("num_qubits"))
    reps = int(circ.get("reps"))
    maxiter = int(opt.get("maxiter", 50))

    # Load and preprocess
    try:
        Xtr, Xte, ytr, yte, shapes, _pp = _load_and_prepare_data(ds, num_qubits, seed=42)
    except Exception as e:
        return {"error": str(e), "received_spec": spec}

    # Build feature encoding + trainable ansatz
    feature_map = ZZFeatureMap(feature_dimension=num_qubits, reps=1)
    ansatz = RealAmplitudes(num_qubits=num_qubits, reps=reps, entanglement="full")

    # Estimator QNN + classifier
    qnn = EstimatorQNN(feature_map=feature_map, ansatz=ansatz, estimator=Estimator())
    clf = NeuralNetworkClassifier(neural_network=qnn, optimizer=COBYLA(maxiter=maxiter))

    clf.fit(Xtr, ytr)
    acc = float(clf.score(Xte, yte))

    result = {
        "message": "Training complete",
        "accuracy": acc,
        "shapes": shapes,
        "num_qubits": num_qubits,
        "reps": reps,
    }

    if bool(outputs.get("return_predictions", True)):
        preds = clf.predict(Xte)
        preview_n = min(10, len(preds))
        result["predictions_preview"] = {
            "y_true": np.asarray(yte[:preview_n]).tolist(),
            "y_pred": np.asarray(preds[:preview_n]).tolist(),
        }

    return result
