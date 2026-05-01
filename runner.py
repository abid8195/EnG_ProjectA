from typing import Dict, Any, List, Tuple
import os
import numpy as np
import pandas as pd

from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import log_loss


def normalize_column_match(df: pd.DataFrame, column_name: str):
    """
    Case-insensitive and whitespace-safe column matching.
    Example: Outcome, outcome, " Outcome " will all match.
    """
    if not column_name:
        return None

    column_map = {str(col).strip().lower(): col for col in df.columns}
    return column_map.get(str(column_name).strip().lower())


def infer_label_column(df: pd.DataFrame):
    """
    Automatically detect likely label column.
    """
    candidates = [
        "label",
        "class",
        "target",
        "y",
        "outcome",
        "species",
        "result",
        "prediction"
    ]

    for candidate in candidates:
        matched = normalize_column_match(df, candidate)
        if matched:
            return matched

    return df.columns[-1] if len(df.columns) > 0 else None


def normalize_feature_columns(df: pd.DataFrame, feature_columns):
    """
    Match requested feature columns safely.
    """
    matched_features = []
    missing_features = []

    for feature in feature_columns:
        matched = normalize_column_match(df, feature)
        if matched:
            matched_features.append(matched)
        else:
            missing_features.append(feature)

    if missing_features:
        raise ValueError(
            f"Feature column(s) {missing_features} not found in CSV headers: {df.columns.tolist()}"
        )

    return matched_features


def validate_pipeline_spec(spec: Dict[str, Any]) -> List[str]:
    """
    Validate pipeline configuration before running.
    """
    errors = []

    if not isinstance(spec, dict):
        return ["Pipeline spec must be a JSON object"]

    dataset = spec.get("dataset", {})
    optimizer = spec.get("optimizer", {})
    circuit = spec.get("circuit", {})

    dataset_type = dataset.get("type", "synthetic-line")

    if dataset_type not in ["synthetic-line", "iris", "csv"]:
        errors.append(f"Unsupported dataset type: {dataset_type}")

    if dataset_type == "csv" and not dataset.get("path"):
        errors.append("CSV dataset requires dataset.path")

    try:
        maxiter = int(optimizer.get("maxiter", 15))
        if maxiter < 1:
            errors.append("optimizer.maxiter must be at least 1")
    except Exception:
        errors.append("optimizer.maxiter must be a valid number")

    try:
        num_qubits = int(circuit.get("num_qubits", 2))
        if num_qubits < 1:
            errors.append("circuit.num_qubits must be at least 1")
    except Exception:
        errors.append("circuit.num_qubits must be a valid number")

    return errors


def resolve_csv_path(csv_path: str) -> str:
    """
    Resolve CSV path relative to backend folder.
    """
    if not csv_path:
        raise ValueError("dataset.path is required for CSV dataset")

    if not os.path.isabs(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), csv_path)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    return csv_path


def prepare_csv_dataset(ds: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Prepare CSV dataset with:
    - case-insensitive label matching
    - case-insensitive feature matching
    - automatic label detection
    - automatic feature fallback
    - numeric feature validation
    """
    seed = int(ds.get("seed", 42))
    csv_path = resolve_csv_path(ds.get("path"))

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError("CSV dataset appears empty")

    original_rows = int(len(df))
    original_columns = [str(col) for col in df.columns.tolist()]

    # Limit rows for demo speed
    df = df.sample(n=min(len(df), 50), random_state=seed)

    requested_label = ds.get("label_column")
    label_column = normalize_column_match(df, requested_label)

    if not label_column:
        label_column = infer_label_column(df)

    if not label_column:
        raise ValueError(
            f"Label column could not be detected. CSV headers: {df.columns.tolist()}"
        )

    requested_features = ds.get("feature_columns") or []

    if requested_features:
        feature_columns = normalize_feature_columns(df, requested_features)
    else:
        feature_columns = [col for col in df.columns if col != label_column]

    if not feature_columns:
        raise ValueError("No valid feature columns detected")

    usable_features = []
    dropped_features = []

    for col in feature_columns:
        numeric_col = pd.to_numeric(df[col], errors="coerce")

        if numeric_col.notna().sum() == 0:
            dropped_features.append(str(col))
        else:
            df[col] = numeric_col.fillna(numeric_col.mean())
            usable_features.append(col)

    if not usable_features:
        raise ValueError(
            "No numeric feature columns available after validation. "
            f"Dropped non-numeric columns: {dropped_features}"
        )

    X = df[usable_features].values
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
                f"CSV label must be binary classification. Found labels: {classes.tolist()}"
            )

        y = np.where(y == classes.max(), 1, -1)

    dataset_summary = {
        "dataset_type": "csv",
        "path": ds.get("path"),
        "rows_original": original_rows,
        "rows_used": int(len(df)),
        "columns": original_columns,
        "label_column": str(label_column),
        "feature_columns": [str(col) for col in usable_features],
        "dropped_features": dropped_features,
        "num_features": int(len(usable_features))
    }

    return X, y, dataset_summary


def build_dataset(ds: Dict[str, Any]):
    """
    Build dataset and return:
    X_train, X_test, y_train, y_test, dataset_summary
    """
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

        dataset_summary = {
            "dataset_type": "synthetic-line",
            "rows_original": int(n),
            "rows_used": int(n),
            "label_column": "generated_label",
            "feature_columns": [f"x{i + 1}" for i in range(d)],
            "num_features": int(d)
        }

        Xtr, Xte, ytr, yte = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=seed
        )

        return Xtr, Xte, ytr, yte, dataset_summary

    if dataset_type == "iris":
        iris = datasets.load_iris()

        X_all = iris.data
        y_all = iris.target

        feat_idx = ds.get("features", [0, 1, 2, 3])
        classes = ds.get("classes", [0, 1])

        mask = np.isin(y_all, classes)

        X = X_all[mask][:, feat_idx]
        y_raw = y_all[mask]
        y = (y_raw == max(classes)).astype(int) * 2 - 1

        feature_names = [iris.feature_names[i] for i in feat_idx]

        dataset_summary = {
            "dataset_type": "iris",
            "rows_original": int(len(X_all)),
            "rows_used": int(len(X)),
            "label_column": "target",
            "feature_columns": feature_names,
            "num_features": int(len(feature_names)),
            "classes_used": classes
        }

        Xtr, Xte, ytr, yte = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=seed
        )

        return Xtr, Xte, ytr, yte, dataset_summary

    if dataset_type == "csv":
        X, y, dataset_summary = prepare_csv_dataset(ds)

        Xtr, Xte, ytr, yte = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=seed
        )

        return Xtr, Xte, ytr, yte, dataset_summary

    raise ValueError(f"Unsupported dataset type: {dataset_type}")


def calculate_convergence_status(accuracy_history, loss_history):
    """
    Simple dashboard interpretation.
    """
    if not accuracy_history or not loss_history:
        return "Not available"

    if len(loss_history) < 2:
        return "Insufficient epochs"

    first_loss = loss_history[0]
    final_loss = loss_history[-1]
    best_accuracy = max(accuracy_history)

    if final_loss < first_loss and best_accuracy >= 0.70:
        return "Improving"

    if final_loss < first_loss:
        return "Loss decreasing"

    if final_loss == first_loss:
        return "Stable"

    return "Needs review"


def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main execution function.
    Adds:
    - pipeline validation
    - dataset summary
    - training progress summary
    - accuracy/loss history
    - exportable training metrics
    """
    validation_errors = validate_pipeline_spec(spec)

    if validation_errors:
        raise ValueError(
            "Pipeline validation failed: " + "; ".join(validation_errors)
        )

    Xtr, Xte, ytr, yte, dataset_summary = build_dataset(
        spec.get("dataset", {})
    )

    scaler = StandardScaler()

    Xtr_scaled = scaler.fit_transform(Xtr)
    Xte_scaled = scaler.transform(Xte)

    maxiter_requested = int(spec.get("optimizer", {}).get("maxiter", 15))
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

        train_predictions = clf.predict(Xtr_scaled)
        train_accuracy = float(np.mean(train_predictions == ytr))

        train_probabilities = clf.predict_proba(Xtr_scaled)
        binary_targets = (ytr == 1).astype(int)

        loss = float(
            log_loss(
                binary_targets,
                train_probabilities[:, 1]
            )
        )

        accuracy_history.append(train_accuracy)
        loss_history.append(loss)

    test_accuracy = float(clf.score(Xte_scaled, yte))
    final_loss = float(loss_history[-1])
    best_train_accuracy = float(max(accuracy_history))
    convergence_status = calculate_convergence_status(
        accuracy_history,
        loss_history
    )

    training_summary = {
        "execution_status": "Completed",
        "best_train_accuracy": best_train_accuracy,
        "final_train_accuracy": float(accuracy_history[-1]),
        "test_accuracy": test_accuracy,
        "final_loss": final_loss,
        "convergence_status": convergence_status,
        "epochs_completed": int(epochs),
        "train_samples": int(len(Xtr)),
        "test_samples": int(len(Xte))
    }

    output = {
        "status": "ok",
        "accuracy": test_accuracy,
        "train_accuracy": float(accuracy_history[-1]),
        "best_train_accuracy": best_train_accuracy,
        "final_loss": final_loss,
        "convergence_status": convergence_status,
        "accuracy_history": accuracy_history,
        "loss_history": loss_history,
        "epochs": epochs,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "dataset_summary": dataset_summary,
        "training_summary": training_summary,
        "spec_echo": spec,
        "note": "Pipeline validated successfully with dataset summary and tracked training metrics"
    }

    if spec.get("outputs", {}).get("return_predictions", True):
        predictions = clf.predict(Xte_scaled)
        output["predictions"] = predictions.tolist()[:20]

    return output