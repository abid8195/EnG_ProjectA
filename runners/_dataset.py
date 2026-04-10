"""
runners/_dataset.py
-------------------
Shared dataset-loading utilities used by all PipelineRunner implementations.
Extracted from the monolithic quantum_runner.py so that both classical and
quantum runners share a single, tested code path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from dataset_catalog import DATASET_CONFIGS


def normalise_label_vector(y: "pd.Series | np.ndarray") -> np.ndarray:
    """
    Coerce an arbitrary label array into a binary integer vector {0, 1}.

    - Numeric arrays that already contain only {0, 1} are cast to int directly.
    - Other numeric arrays are median-binarised.
    - String/object arrays must have exactly two unique values; the
      lexicographically larger class maps to 1.
    """
    values = np.asarray(y)

    if values.dtype.kind in "biuf":
        unique = np.unique(values)
        if set(unique.tolist()) <= {0, 1}:
            return values.astype(int)
        return (values > np.median(values)).astype(int)

    classes = np.unique(values)
    if len(classes) != 2:
        raise ValueError(
            f"Binary classification is required; got labels {classes.tolist()}"
        )
    return np.where(values == classes.max(), 1, 0).astype(int)


def load_dataset_from_csv(
    csv_path: Path, ds: Dict[str, Any]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load feature matrix X and label vector y from a CSV file.

    Parameters
    ----------
    csv_path : Path
        Absolute path to the CSV file.
    ds : dict
        Dataset spec containing at minimum ``label_column`` and
        ``feature_columns``.

    Returns
    -------
    X : np.ndarray, shape (n_samples, n_features)
    y : np.ndarray, shape (n_samples,), dtype int, values in {0, 1}
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV appears to be empty")

    label_column = ds.get("label_column")
    feature_columns = ds.get("feature_columns") or []

    if not label_column:
        raise ValueError("dataset.label_column is required")
    if not feature_columns:
        raise ValueError("dataset.feature_columns is required")

    required = [label_column, *feature_columns]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing dataset columns: {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )

    X = df[feature_columns].astype(float).to_numpy()
    y = normalise_label_vector(df[label_column])
    return X, y


def resolve_dataset_spec(ds: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resolve a dataset spec dict into (X, y) arrays.

    Supported sources
    -----------------
    - Named catalog entry: ``{"name": "finance"}``
    - Arbitrary CSV: ``{"type": "csv", "path": "...", "label_column": "...",
                        "feature_columns": [...]}``
    """
    dataset_type = (ds.get("type") or "csv").lower()
    dataset_name = ds.get("name")

    if dataset_name and dataset_name in DATASET_CONFIGS:
        config = DATASET_CONFIGS[dataset_name]
        merged = {
            "label_column": config["label_column"],
            "feature_columns": config["feature_columns"],
            **ds,
        }
        return load_dataset_from_csv(Path(config["path"]), merged)

    if dataset_type == "csv":
        raw_path = ds.get("path")
        if not raw_path:
            raise ValueError("dataset.path is required for CSV datasets")
        csv_path = Path(raw_path)
        if not csv_path.is_absolute():
            # Resolve relative paths against the project root (two levels up
            # from this file: runners/ → project root)
            csv_path = Path(__file__).resolve().parents[1] / raw_path
        return load_dataset_from_csv(csv_path, ds)

    raise ValueError(f"Unsupported dataset type: {dataset_type!r}")
