# backend/runner.py  — Sprint 2
from typing import Dict, Any, List
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
    Sprint 2: added finance, hr, supply_chain dataset types.
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
        y = (np.sum(X, axis=1) >= 0).astype(int) * 2 - 1
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "iris":
        iris = datasets.load_iris()
        X_all, y_all = iris.data, iris.target
        feat_idx = ds.get("features", [0, 1, 2, 3])
        classes = ds.get("classes", [0, 1])
        mask = np.isin(y_all, classes)
        X = X_all[mask][:, feat_idx]
        y_raw = y_all[mask]
        y = (y_raw == max(classes)).astype(int) * 2 - 1
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "csv":
        csv_path = ds.get("path")
        if not csv_path:
            raise ValueError("dataset.path is required for CSV")
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), csv_path)
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("CSV appears to be empty")
        df = df.sample(n=min(len(df), 50), random_state=seed)
        label_col = ds.get("label_column")
        feat_cols = ds.get("feature_columns") or []
        if not label_col:
            raise ValueError("dataset.label_column is required for CSV")
        for c in [label_col, *feat_cols]:
            if c not in df.columns:
                raise ValueError(f"Column '{c}' not in CSV headers: {df.columns.tolist()}")
        X = df[feat_cols].values.astype(float)
        y = df[label_col].values
        if y.dtype.kind in "biuf":
            uniq = np.unique(y)
            if set(uniq) <= {0, 1}:
                y = np.where(y == 1, 1, -1)
            else:
                y = np.where(y > 0, 1, -1)
        else:
            classes_arr = np.unique(y)
            if len(classes_arr) != 2:
                raise ValueError(f"CSV label must be binary; got {classes_arr.tolist()}")
            y = np.where(y == classes_arr.max(), 1, -1)
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "finance":
        rng = np.random.RandomState(seed)
        n = int(ds.get("num_samples", 80))
        X = rng.randn(n, 5)
        y = np.where((X[:, 0] < 0) & (X[:, 2] > 0), 1, -1)
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "hr":
        rng = np.random.RandomState(seed)
        n = int(ds.get("num_samples", 80))
        X = rng.randn(n, 5)
        y = np.where((X[:, 0] > 0) & (X[:, 3] < 0.5), 1, -1)
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    elif kind == "supply_chain":
        rng = np.random.RandomState(seed)
        n = int(ds.get("num_samples", 80))
        X = rng.randn(n, 5)
        y = np.where((X[:, 3] > 0) & (X[:, 2] > -0.5), 1, -1)
        return train_test_split(X, y, test_size=test_size, random_state=seed)

    else:
        raise ValueError(f"Unknown dataset type: {kind}")


def _run_pipeline_classical(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classical ML pipeline using LogisticRegression.
    Simple and robust — works with basic Python packages.
    """
    Xtr, Xte, ytr, yte = _build_dataset(spec.get("dataset", {}))

    scaler = StandardScaler()
    Xtr_scaled = scaler.fit_transform(Xtr)
    Xte_scaled = scaler.transform(Xte)

    requested_maxiter = int(spec.get("optimizer", {}).get("maxiter", 100))
    maxiter = max(1, min(requested_maxiter, 1000))

    clf = LogisticRegression(max_iter=maxiter, random_state=42)
    clf.fit(Xtr_scaled, ytr)

    train_acc = float(clf.score(Xtr_scaled, ytr))
    test_acc = float(clf.score(Xte_scaled, yte))

    out = {
        "execution_mode": "classical",
        "accuracy": test_acc,
        "train_accuracy": train_acc,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "spec_echo": spec,
        "note": "Classical LogisticRegression execution."
    }

    if spec.get("outputs", {}).get("return_predictions", True):
        predictions = clf.predict(Xte_scaled)
        out["predictions"] = predictions.tolist()[:20]

    return out


def _validate_kipu_sprint2(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sprint 2 validation: accept any binary-compatible dataset type.
    Encoder must be angle. Optimizer must be cobyla.
    Circuit: ry or efficientsu2.
    """
    enc = spec.get("encoder", {}) or {}
    cir = spec.get("circuit", {}) or {}
    opt = spec.get("optimizer", {}) or {}

    encoder_type = str(enc.get("type", "")).lower()
    circuit_type = str(cir.get("type", "")).lower()
    optimizer_type = str(opt.get("type", "")).lower()

    if encoder_type not in ("angle", "basis", ""):
        raise ValueError(
            f"Unsupported encoder '{encoder_type}'. "
            "Sprint 2 supports: angle, basis."
        )
    if optimizer_type not in ("cobyla", ""):
        raise ValueError(
            f"Unsupported optimizer '{optimizer_type}'. "
            "Sprint 2 supports: cobyla."
        )
    if circuit_type not in ("ry", "efficientsu2", "realamplitudes", ""):
        raise ValueError(
            f"Unsupported circuit '{circuit_type}'. "
            "Sprint 2 supports: ry, efficientsu2, realamplitudes."
        )

    num_qubits = int(cir.get("num_qubits", 2) or 2)
    if not (1 <= num_qubits <= 6):
        raise ValueError("Sprint 2 supports 1..6 qubits.")

    reps = int(cir.get("reps", 1) or 1)
    reps = max(1, min(reps, 3))

    return {
        "num_qubits": num_qubits,
        "reps": reps,
        "circuit_type": circuit_type or "ry",
        "encoder_type": encoder_type or "angle",
        "shots": int(spec.get("quantum", {}).get("shots", 100) or 100),
        "maxiter": int(opt.get("maxiter", 15) or 15),
    }


def _run_pipeline_kipu_simulator(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sprint 2 quantum execution.
    - Tries Kipu Quantum Hub first (requires KIPU_ACCESS_TOKEN).
    - Falls back to qiskit_aer.AerSimulator if token missing/invalid.
    - Supports all Sprint 2 dataset types (not just iris).
    """
    cfg = _validate_kipu_sprint2(spec)

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit.circuit.library import ZZFeatureMap, TwoLocal, EfficientSU2, RealAmplitudes
        from qiskit_algorithms.optimizers import COBYLA
        from sklearn.preprocessing import MinMaxScaler
    except ImportError as e:
        raise ValueError(f"Missing required quantum dependencies: {e}")

    backend = None
    backend_label = "unknown"

    kipu_token = os.getenv("KIPU_ACCESS_TOKEN", "").strip()
    if kipu_token:
        try:
            from kipu_adapter import get_kipu_backend
            backend = get_kipu_backend()
            backend_label = "kipu_hub"
        except Exception as kipu_err:
            print(f"[runner] Kipu backend failed ({kipu_err}), falling back to AerSimulator.")

    if backend is None:
        try:
            from qiskit_aer import AerSimulator
            backend = AerSimulator()
            backend_label = "aer_simulator"
        except ImportError:
            raise ValueError(
                "Neither Kipu backend nor qiskit-aer is available. "
                "Install qiskit-aer or set KIPU_ACCESS_TOKEN."
            )

    ds_spec = dict(spec.get("dataset", {}) or {})
    Xtr, Xte, ytr, yte = _build_dataset(ds_spec)

    num_qubits = cfg["num_qubits"]
    feature_dim = min(Xtr.shape[1], num_qubits)
    Xtr = Xtr[:, :feature_dim]
    Xte = Xte[:, :feature_dim]

    reps = cfg["reps"]
    circuit_type = cfg["circuit_type"]
    shots = cfg["shots"]

    scaler = MinMaxScaler(feature_range=(0.0, 2.0 * np.pi))
    Xtr_angles = scaler.fit_transform(Xtr)
    Xte_angles = scaler.transform(Xte)

    feature_map = ZZFeatureMap(feature_dimension=feature_dim, reps=1)
    if circuit_type == "ry":
        ansatz = TwoLocal(
            num_qubits=feature_dim,
            rotation_blocks="ry",
            entanglement_blocks="cx",
            reps=reps,
        )
    elif circuit_type == "realamplitudes":
        ansatz = RealAmplitudes(num_qubits=feature_dim, reps=reps)
    else:
        ansatz = EfficientSU2(num_qubits=feature_dim, reps=reps)

    weight_params = sorted(list(ansatz.parameters), key=lambda p: str(p))
    input_params = sorted(list(feature_map.parameters), key=lambda p: str(p))

    if not weight_params:
        raise ValueError("No trainable parameters found for the selected ansatz.")
    if len(input_params) != feature_dim:
        raise ValueError(
            f"Feature-map parameter count mismatch: expected {feature_dim}, "
            f"got {len(input_params)}."
        )

    qc = QuantumCircuit(feature_dim, 1)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz, inplace=True)
    qc.measure(0, 0)

    try:
        qc_t = transpile(qc, backend=backend, optimization_level=1)
    except Exception as e:
        raise ValueError(f"Transpilation failed: {e}")

    def _bind_input(qc_template, x_vec):
        bind = {input_params[i]: float(x_vec[i]) for i in range(feature_dim)}
        return qc_template.assign_parameters(bind, inplace=False)

    def _expectation(counts):
        count0 = int(counts.get("0", 0))
        count1 = int(counts.get("1", 0))
        total = count0 + count1 or 1
        return (count0 - count1) / float(total)

    rng = np.random.RandomState(int(ds_spec.get("seed", 42) or 42))
    train_eval_n = min(8, len(Xtr_angles))
    idx_eval = rng.choice(len(Xtr_angles), size=train_eval_n, replace=False)
    Xtr_eval = Xtr_angles[idx_eval]
    ytr_eval = ytr[idx_eval]

    qc_tr_eval = [_bind_input(qc_t, Xtr_eval[i]) for i in range(len(Xtr_eval))]
    qc_te = [_bind_input(qc_t, Xte_angles[i]) for i in range(len(Xte_angles))]

    loss_history: List[float] = []
    accuracy_history: List[float] = []

    def objective(theta):
        theta = np.asarray(theta, dtype=float)
        theta_bind = {weight_params[i]: float(theta[i]) for i in range(len(weight_params))}
        qc_list = [qc_x.assign_parameters(theta_bind, inplace=False) for qc_x in qc_tr_eval]
        try:
            job = backend.run(qc_list, shots=shots)
            res = job.result()
        except Exception as e:
            raise ValueError(f"Backend execution failed: {e}")
        correct = 0
        for i, y_true in enumerate(ytr_eval):
            counts = res.get_counts(i)
            y_pred = 1 if _expectation(counts) >= 0.0 else -1
            if int(y_pred) == int(y_true):
                correct += 1
        acc = correct / float(len(ytr_eval))
        loss_history.append(1.0 - acc)
        accuracy_history.append(acc)
        return 1.0 - acc

    optimizer = COBYLA(maxiter=cfg["maxiter"])
    x0 = rng.uniform(low=-np.pi, high=np.pi, size=len(weight_params))

    try:
        opt_result = optimizer.minimize(objective, x0=x0)
    except Exception as e:
        raise ValueError(f"Optimization failed: {e}")

    theta_opt = np.asarray(opt_result.x, dtype=float)
    theta_bind_opt = {weight_params[i]: float(theta_opt[i]) for i in range(len(weight_params))}

    qc_te_bound = [qc_x.assign_parameters(theta_bind_opt, inplace=False) for qc_x in qc_te]
    try:
        job = backend.run(qc_te_bound, shots=shots)
        res = job.result()
    except Exception as e:
        raise ValueError(f"Backend test execution failed: {e}")

    preds = []
    correct_te = 0
    for i, y_true in enumerate(yte):
        counts = res.get_counts(i)
        y_pred = 1 if _expectation(counts) >= 0.0 else -1
        preds.append(int(y_pred))
        if int(y_pred) == int(y_true):
            correct_te += 1

    test_acc = correct_te / float(len(yte))

    qc_tr_bound = [qc_x.assign_parameters(theta_bind_opt, inplace=False) for qc_x in qc_tr_eval]
    try:
        job = backend.run(qc_tr_bound, shots=shots)
        res_tr = job.result()
    except Exception as e:
        raise ValueError(f"Backend train evaluation failed: {e}")

    correct_tr = sum(
        1 for i, y_true in enumerate(ytr_eval)
        if (1 if _expectation(res_tr.get_counts(i)) >= 0.0 else -1) == int(y_true)
    )
    train_acc = correct_tr / float(len(ytr_eval))

    out = {
        "execution_mode": f"quantum ({backend_label})",
        "accuracy": float(test_acc),
        "train_accuracy": float(train_acc),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "spec_echo": spec,
        "note": f"Quantum execution via {backend_label}. Dataset: {ds_spec.get('type','?')}.",
        "loss_history": loss_history,
        "accuracy_history": accuracy_history,
        "epochs": len(loss_history),
    }

    if spec.get("outputs", {}).get("return_predictions", True):
        out["predictions"] = preds[:20]

    return out


def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch pipeline execution based on spec.execution_mode.

    Sprint 2 supported modes:
    - classical        : LogisticRegression (always works, no Qiskit needed)
    - kipu_simulator   : Quantum — tries Kipu Hub, falls back to AerSimulator
    """
    mode = str((spec or {}).get("execution_mode", "classical") or "classical").lower()
    if mode == "kipu_simulator":
        return _run_pipeline_kipu_simulator(spec)
    return _run_pipeline_classical(spec)
