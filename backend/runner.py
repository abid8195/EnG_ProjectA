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

<<<<<<< HEAD
def _run_pipeline_classical(spec: Dict[str, Any]) -> Dict[str, Any]:
=======
def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
>>>>>>> 9d1b400665006b6b0c73aa61d45b7355aac41cf1
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
    
<<<<<<< HEAD
    return out


def _validate_kipu_sprint1(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that `spec` matches the Sprint 1 supported pathway:
    - dataset: iris (dataset.type == 'iris')
    - encoder: angle (encoder.type == 'angle')
    - circuit: ry or efficientsu2
    - optimizer: cobyla
    """
    ds = spec.get("dataset", {}) or {}
    enc = spec.get("encoder", {}) or {}
    cir = spec.get("circuit", {}) or {}
    opt = spec.get("optimizer", {}) or {}

    dataset_type = str(ds.get("type", "")).lower()
    encoder_type = str(enc.get("type", "")).lower()
    circuit_type = str(cir.get("type", "")).lower()
    optimizer_type = str(opt.get("type", "")).lower()

    dataset_is_iris_csv = dataset_type == "csv" and str(ds.get("label_column", "")).lower() == "species"
    if dataset_type != "iris" and not dataset_is_iris_csv:
        raise ValueError(
            "Unsupported dataset for kipu_simulator. Only dataset.type='iris' is supported in Sprint 1 "
            "(or dataset.type='csv' with iris-like label_column='species')."
        )
    if encoder_type != "angle":
        raise ValueError("Unsupported encoder for kipu_simulator. Only encoder.type='angle' is supported in Sprint 1.")
    if optimizer_type != "cobyla":
        raise ValueError("Unsupported optimizer for kipu_simulator. Only optimizer.type='cobyla' is supported in Sprint 1.")
    if circuit_type not in ("ry", "efficientsu2"):
        raise ValueError(
            "Unsupported circuit for kipu_simulator. Only circuit.type='ry' or circuit.type='efficientsu2' is supported in Sprint 1."
        )

    num_qubits = int(cir.get("num_qubits", 2) or 2)
    if not (1 <= num_qubits <= 4):
        raise ValueError("Unsupported circuit.num_qubits. Sprint 1 supports 1..4 qubits.")

    reps = int(cir.get("reps", 1) or 1)
    # Clamp for demo runtime. (Frontend allows larger values; Sprint 1 keeps it light.)
    reps = max(1, min(reps, 2))

    return {
        "num_qubits": num_qubits,
        "reps": reps,
        "circuit_type": circuit_type,
        "shots": int(spec.get("quantum", {}).get("shots", 100) or 100),
        "maxiter": int(opt.get("maxiter", 15) or 15),
    }


def _run_pipeline_kipu_simulator(spec: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _validate_kipu_sprint1(spec)

    try:
        from kipu_adapter import get_kipu_backend
    except Exception as e:
        raise ValueError(f"Kipu adapter setup failed: {e}")

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit.circuit.library import ZZFeatureMap, TwoLocal, EfficientSU2
        from qiskit_algorithms.optimizers import COBYLA
        from sklearn.preprocessing import MinMaxScaler
    except ImportError as e:
        raise ValueError(f"Missing required quantum dependencies: {e}")

    # Build dataset (binary iris demo).
    ds_spec = spec.get("dataset", {}) or {}
    # If the UI passes the iris dataset as CSV, map it to the binary sklearn iris pathway.
    if str(ds_spec.get("type", "")).lower() == "csv":
        ds_spec = dict(ds_spec)
        ds_spec["type"] = "iris"
    Xtr, Xte, ytr, yte = _build_dataset(ds_spec)

    num_qubits = cfg["num_qubits"]

    # For Sprint 1 we require the circuit qubit count to be <= feature count.
    if Xtr.shape[1] < num_qubits:
        raise ValueError(
            f"Unsupported configuration: circuit.num_qubits={num_qubits} exceeds dataset feature count={Xtr.shape[1]}."
        )
    if Xtr.shape[1] > num_qubits:
        Xtr = Xtr[:, :num_qubits]
        Xte = Xte[:, :num_qubits]

    feature_dim = Xtr.shape[1]
    reps = cfg["reps"]
    circuit_type = cfg["circuit_type"]
    shots = cfg["shots"]

    # Scale input data to a rotation-friendly range for angle encoding.
    scaler = MinMaxScaler(feature_range=(0.0, 2.0 * np.pi))
    Xtr_angles = scaler.fit_transform(Xtr)
    Xte_angles = scaler.transform(Xte)

    # Build feature map + ansatz + 1-qubit measurement circuit (Z on qubit 0).
    feature_map = ZZFeatureMap(feature_dimension=feature_dim, reps=1)
    if circuit_type == "ry":
        ansatz = TwoLocal(
            num_qubits=feature_dim,
            rotation_blocks="ry",
            entanglement_blocks="cx",
            reps=reps,
        )
    else:
        ansatz = EfficientSU2(num_qubits=feature_dim, reps=reps)

    weight_params = sorted(list(ansatz.parameters), key=lambda p: str(p))
    if not weight_params:
        raise ValueError("No trainable parameters found for the selected ansatz.")

    input_params = sorted(list(feature_map.parameters), key=lambda p: str(p))
    if len(input_params) != feature_dim:
        raise ValueError(
            f"Unexpected feature-map parameter count: expected {feature_dim}, got {len(input_params)}."
        )

    qc = QuantumCircuit(feature_dim, 1)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz, inplace=True)
    qc.measure(0, 0)

    # Pre-create Kipu backend + transpiled circuit template.
    try:
        backend = get_kipu_backend()
        qc_t = transpile(qc, backend=backend, optimization_level=1)
    except Exception as e:
        raise ValueError(f"Kipu backend init failed: {e}")

    def _bind_input(qc_template, x_vec: np.ndarray):
        bind = {input_params[i]: float(x_vec[i]) for i in range(feature_dim)}
        return qc_template.assign_parameters(bind, inplace=False)

    def _expectation_from_counts(counts: Dict[str, int]) -> float:
        # With a single measured classical bit, counts keys are typically '0' and '1'.
        count0 = int(counts.get("0", 0))
        count1 = int(counts.get("1", 0))
        return (count0 - count1) / float(shots)  # <Z>

    # Use small subsets during optimization for a light Sprint 1 demo.
    rng = np.random.RandomState(int(spec.get("dataset", {}).get("seed", 42) or 42))
    train_eval_n = min(8, len(Xtr_angles))
    if len(Xtr_angles) > train_eval_n:
        idx_eval = rng.choice(len(Xtr_angles), size=train_eval_n, replace=False)
    else:
        idx_eval = np.arange(len(Xtr_angles))

    Xtr_eval = Xtr_angles[idx_eval]
    ytr_eval = ytr[idx_eval]

    qc_tr_eval = [_bind_input(qc_t, Xtr_eval[i]) for i in range(len(Xtr_eval))]
    qc_te = [_bind_input(qc_t, Xte_angles[i]) for i in range(len(Xte_angles))]

    # COBYLA objective: minimize misclassification error on the eval subset.
    loss_history = []
    accuracy_history = []

    def objective(theta: np.ndarray) -> float:
        theta = np.asarray(theta, dtype=float)
        if theta.shape[0] != len(weight_params):
            raise ValueError("Optimizer provided theta with unexpected length.")

        theta_bind = {weight_params[i]: float(theta[i]) for i in range(len(weight_params))}
        qc_list = [qc_x.assign_parameters(theta_bind, inplace=False) for qc_x in qc_tr_eval]

        try:
            job = backend.run(qc_list, shots=shots)
            res = job.result()
        except Exception as e:
            raise ValueError(f"Kipu simulator execution failed: {e}")

        correct = 0
        for i, y_true in enumerate(ytr_eval):
            counts = res.get_counts(i)
            exp_z = _expectation_from_counts(counts)
            y_pred = 1 if exp_z >= 0.0 else -1
            if int(y_pred) == int(y_true):
                correct += 1

        acc = correct / float(len(ytr_eval))
        loss = 1.0 - acc
        loss_history.append(float(loss))
        accuracy_history.append(float(acc))
        return float(loss)

    optimizer = COBYLA(maxiter=cfg["maxiter"])
    x0 = rng.uniform(low=-np.pi, high=np.pi, size=len(weight_params))

    try:
        opt_result = optimizer.minimize(objective, x0=x0)
    except Exception as e:
        raise ValueError(f"Kipu optimization failed: {e}")

    theta_opt = np.asarray(opt_result.x, dtype=float)

    # Final prediction (test set).
    theta_bind_opt = {weight_params[i]: float(theta_opt[i]) for i in range(len(weight_params))}
    qc_te_bound = [qc_x.assign_parameters(theta_bind_opt, inplace=False) for qc_x in qc_te]
    try:
        job = backend.run(qc_te_bound, shots=shots)
        res = job.result()
    except Exception as e:
        raise ValueError(f"Kipu simulator execution failed during evaluation: {e}")

    preds = []
    correct_te = 0
    for i, y_true in enumerate(yte):
        counts = res.get_counts(i)
        exp_z = _expectation_from_counts(counts)
        y_pred = 1 if exp_z >= 0.0 else -1
        preds.append(int(y_pred))
        if int(y_pred) == int(y_true):
            correct_te += 1

    test_acc = correct_te / float(len(yte))

    # Compute lightweight train accuracy on the eval subset used during optimization.
    qc_tr_eval_bound = [qc_x.assign_parameters(theta_bind_opt, inplace=False) for qc_x in qc_tr_eval]
    try:
        job = backend.run(qc_tr_eval_bound, shots=shots)
        res_tr = job.result()
    except Exception as e:
        raise ValueError(f"Kipu simulator execution failed during train evaluation: {e}")

    correct_tr = 0
    for i, y_true in enumerate(ytr_eval):
        counts = res_tr.get_counts(i)
        exp_z = _expectation_from_counts(counts)
        y_pred = 1 if exp_z >= 0.0 else -1
        if int(y_pred) == int(y_true):
            correct_tr += 1

    train_acc = correct_tr / float(len(ytr_eval))

    out = {
        "execution_mode": "kipu_simulator",
        "accuracy": float(test_acc),
        "train_accuracy": float(train_acc),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "spec_echo": spec,
        "note": "Executed via Kipu Quantum Hub simulator (binary iris demo).",
        "loss_history": loss_history,
        "accuracy_history": accuracy_history,
        "epochs": len(loss_history),
    }

    if spec.get("outputs", {}).get("return_predictions", True):
        out["predictions"] = preds[:20]

    return out


def run_pipeline(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch pipeline execution based on `spec.execution_mode`.

    Supported:
    - classical (default): existing LogisticRegression behavior
    - kipu_simulator: Sprint 1 quantum-simulator pathway (iris/angle/ry+efficientSU2/cobyla)
    """
    mode = str((spec or {}).get("execution_mode", "classical") or "classical").lower()
    if mode == "kipu_simulator":
        return _run_pipeline_kipu_simulator(spec)
    return _run_pipeline_classical(spec)
=======
    return out
>>>>>>> 9d1b400665006b6b0c73aa61d45b7355aac41cf1
