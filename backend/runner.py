# backend/runner.py
from typing import Dict, Any
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import datasets
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

def _build_dataset(ds: Dict[str, Any]):
    """
    Return X_train, X_test, y_train, y_test based on dataset spec.
    """
    seed = int(ds.get("seed", 42))
    np.random.seed(seed)
    test_size = float(ds.get("test_size", 0.2))
    if not (0.05 <= test_size <= 0.5):
        test_size = 0.2

    kind = ds.get("type", "synthetic-line")

    if kind == "synthetic-line":
        n = int(ds.get("num_samples", 24))
        d = int(ds.get("num_features", 2))
        X = 2 * np.random.random([n, d]) - 1
        y = (np.sum(X, axis=1) >= 0).astype(int) * 2 - 1  # -1/+1
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "iris":
        iris = datasets.load_iris()
        X_all, y_all = iris.data, iris.target
        feat_idx = ds.get("features", [0, 1, 2, 3])  # can be narrowed by UI
        classes = ds.get("classes", [0, 1])         # binary for this demo
        mask = np.isin(y_all, classes)
        X = X_all[mask][:, feat_idx]
        y_raw = y_all[mask]
        y = (y_raw == max(classes)).astype(int) * 2 - 1
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "csv":
        csv_path = ds.get("path")
        if not csv_path:
            raise ValueError("dataset.path is required for CSV")

        # Allow relative path like 'uploads/file.csv' from app.py
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), csv_path)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("CSV appears to be empty")

        # throttle rows to keep demo fast
        df = df.sample(n=min(len(df), 50), random_state=seed)

        label_col = ds.get("label_column")
        feat_cols = ds.get("feature_columns") or []
        if not label_col:
            raise ValueError("dataset.label_column is required for CSV")
        for c in [label_col, *feat_cols]:
            if c not in df.columns:
                raise ValueError(f"Column '{c}' not in CSV headers: {df.columns.tolist()}")

        X = df[feat_cols].values
        y = df[label_col].values

        # map labels to {-1,+1}
        if y.dtype.kind in "biuf":
            uniq = np.unique(y)
            if set(uniq) <= {0, 1}:
                y = np.where(y == 1, 1, -1)
            else:
                y = np.where(y > 0, 1, -1)
        else:
            classes = np.unique(y)
            if len(classes) != 2:
                raise ValueError(f"CSV label must be binary; got {classes.tolist()}")
            y = np.where(y == classes.max(), 1, -1)

        return train_test_split(X, y, test_size=test_size, random_state=seed)

    else:
        raise ValueError(f"Unknown dataset type: {kind}")

def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classical ML pipeline using LogisticRegression.
    Simple and robust - works with basic Python packages.
    """
    Xtr, Xte, ytr, yte = _build_dataset(spec.get("dataset", {}))

    # Preprocess data
    scaler = StandardScaler()
    Xtr_scaled = scaler.fit_transform(Xtr)
    Xte_scaled = scaler.transform(Xte)

    # Train classifier
    requested_maxiter = int(spec.get("optimizer", {}).get("maxiter", 100))
    maxiter = max(1, min(requested_maxiter, 1000))  # reasonable bounds
    
    clf = LogisticRegression(max_iter=maxiter, random_state=42)
    clf.fit(Xtr_scaled, ytr)
    
    # Evaluate
    train_acc = float(clf.score(Xtr_scaled, ytr))
    test_acc = float(clf.score(Xte_scaled, yte))

    out = {
        "accuracy": test_acc,
        "train_accuracy": train_acc,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "spec_echo": spec,
        "note": "Using classical LogisticRegression (quantum ML components not available)"
    }
    
    if spec.get("outputs", {}).get("return_predictions", True):
        predictions = clf.predict(Xte_scaled)
        out["predictions"] = predictions.tolist()[:20]  # limit output size
    
    return out