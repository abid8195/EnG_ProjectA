from typing import Dict, Any
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import datasets
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import log_loss


def normalize_column_match(df: pd.DataFrame, column_name: str):
    """
    Case-insensitive + whitespace-safe column matching.
    """
    if not column_name:
        return None

    normalized_cols = {
        str(col).strip().lower(): col for col in df.columns
    }

    return normalized_cols.get(column_name.strip().lower())


def normalize_feature_columns(df: pd.DataFrame, feature_columns):
    """
    Match feature columns safely with fallback detection.
    """
    if not feature_columns:
        return []

    matched = []
    missing = []

    for feature in feature_columns:
        col = normalize_column_match(df, feature)

        if col:
            matched.append(col)
        else:
            missing.append(feature)

    if missing:
        raise ValueError(
            f"Feature column(s) {missing} not found in CSV headers: {df.columns.tolist()}"
        )

    return matched


def _build_dataset(ds: Dict[str, Any]):

    seed = int(ds.get("seed", 42))
    np.random.seed(seed)

    test_size = float(ds.get("test_size", 0.2))

    if not (0.05 <= test_size <= 0.5):
        test_size = 0.2

    dataset_type = ds.get("type", "synthetic-line")

    if dataset_type == "synthetic-line":

        n = int(ds.get("num_samples", 24))
        d = int(ds.get("num_features", 2))

        X = 2 * np.random.random([n, d]) - 1
        y = (np.sum(X, axis=1) >= 0).astype(int) * 2 - 1

        return train_test_split(X, y, test_size=test_size, random_state=seed)


    elif dataset_type == "iris":

        iris = datasets.load_iris()

        X_all = iris.data
        y_all = iris.target

        feat_idx = ds.get("features", [0, 1, 2, 3])
        classes = ds.get("classes", [0, 1])

        mask = np.isin(y_all, classes)

        X = X_all[mask][:, feat_idx]

        y_raw = y_all[mask]

        y = (y_raw == max(classes)).astype(int) * 2 - 1

        return train_test_split(X, y, test_size=test_size, random_state=seed)


    elif dataset_type == "csv":

        csv_path = ds.get("path")

        if not csv_path:
            raise ValueError("dataset.path is required for CSV dataset")

        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), csv_path)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        if df.empty:
            raise ValueError("CSV dataset appears empty")

        df = df.sample(n=min(len(df), 50), random_state=seed)

        requested_label = ds.get("label_column")

        label_column = normalize_column_match(df, requested_label)

        if not label_column:
            raise ValueError(
                f"Label column '{requested_label}' not found in CSV headers: {df.columns.tolist()}"
            )

        requested_features = ds.get("feature_columns") or []

        if requested_features:

            feature_columns = normalize_feature_columns(
                df,
                requested_features
            )

        else:

            feature_columns = [
                col for col in df.columns
                if col != label_column
            ]

        if not feature_columns:
            raise ValueError("No valid feature columns detected")

        X = df[feature_columns].values

        y = df[label_column].values

        if y.dtype.kind in "biuf":

            unique_vals = np.unique(y)

            if set(unique_vals) <= {0, 1}:

                y = np.where(y == 1, 1, -1)

            else:

                y = np.where(y > 0, 1, -1)

        else:

            classes = np.unique(y)

            if len(classes) != 2:

                raise ValueError(
                    f"CSV label must be binary classification. Found {classes.tolist()}"
                )

            y = np.where(y == classes.max(), 1, -1)

        return train_test_split(X, y, test_size=test_size, random_state=seed)


    else:

        raise ValueError(f"Unsupported dataset type: {dataset_type}")


def run_pipeline(spec: Dict[str, Any]):

    Xtr, Xte, ytr, yte = _build_dataset(spec.get("dataset", {}))

    scaler = StandardScaler()

    Xtr_scaled = scaler.fit_transform(Xtr)

    Xte_scaled = scaler.transform(Xte)

    maxiter_requested = int(
        spec.get("optimizer", {}).get("maxiter", 15)
    )

    epochs = max(1, min(maxiter_requested, 20))

    clf = SGDClassifier(
        loss="log_loss",
        random_state=42
    )

    accuracy_history = []

    loss_history = []

    classes = np.unique(ytr)

    for _ in range(epochs):

        clf.partial_fit(
            Xtr_scaled,
            ytr,
            classes=classes
        )

        preds = clf.predict(Xtr_scaled)

        train_accuracy = float(np.mean(preds == ytr))

        probabilities = clf.predict_proba(Xtr_scaled)

        targets_binary = (ytr == 1).astype(int)

        loss = float(
            log_loss(
                targets_binary,
                probabilities[:, 1]
            )
        )

        accuracy_history.append(train_accuracy)

        loss_history.append(loss)

    test_accuracy = float(
        clf.score(
            Xte_scaled,
            yte
        )
    )

    return {

        "status": "ok",

        "accuracy": test_accuracy,

        "train_accuracy": accuracy_history[-1],

        "accuracy_history": accuracy_history,

        "loss_history": loss_history,

        "epochs": epochs,

        "n_train": int(len(Xtr)),

        "n_test": int(len(Xte)),

        "note": "Improved dataset compatibility + tracked training metrics"
    }