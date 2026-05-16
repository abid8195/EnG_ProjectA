from pathlib import Path


def write_generated_run(spec: dict, out_path: str | None = None) -> str:
    """
    Compatibility code generator used by older backend tooling.
    """
    framework = (spec.get("framework") or "qiskit").lower()
    dataset = spec.get("dataset", {})
    circuit = spec.get("circuit", {})
    optimizer = spec.get("optimizer", {})
    execution = spec.get("execution", {})

    if out_path is None:
        out_path = Path(__file__).resolve().parents[1] / "generated_run.py"

    if framework == "pennylane":
        code = f"""# Auto-generated PennyLane template
import pennylane as qml
from pennylane import numpy as np
import pandas as pd

df = pd.read_csv("{dataset.get("path", "<path-to-csv>")}")
X = df[{dataset.get("feature_columns", [])!r}].astype(float).to_numpy()
y = df["{dataset.get("label_column", "label")}"].astype(int).to_numpy()

dev = qml.device("default.qubit", wires={max(1, int(circuit.get("num_qubits", 2)))}, shots={max(32, int(execution.get("shots", 128)))})

@qml.qnode(dev)
def circuit_fn(features, weights):
    qml.AngleEmbedding(features[:{max(1, int(circuit.get("num_qubits", 2)))}], wires=range({max(1, int(circuit.get("num_qubits", 2)))}), rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=range({max(1, int(circuit.get("num_qubits", 2)))}))
    return qml.expval(qml.PauliZ(0))

weights = np.random.random(({max(1, int(circuit.get("reps", 2)))}, {max(1, int(circuit.get("num_qubits", 2)))}, 3), requires_grad=True)
print("Template ready for PennyLane training.")
"""
    else:
        optimizer_name = str(optimizer.get("type", "cobyla")).upper()
        feature_map = "PauliFeatureMap" if dataset.get("type") == "basis" else "ZZFeatureMap"
        code = f"""# Auto-generated Qiskit template
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from qiskit.circuit.library import {feature_map}, RealAmplitudes
from qiskit_machine_learning.algorithms.classifiers import VQC
from qiskit_algorithms.optimizers import {optimizer_name}
from qiskit.primitives import BackendSamplerV2
from qiskit_aer import AerSimulator

df = pd.read_csv("{dataset.get("path", "<path-to-csv>")}")
X = df[{dataset.get("feature_columns", [])!r}].astype(float).to_numpy()
y = df["{dataset.get("label_column", "label")}"].astype(int).to_numpy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={float(dataset.get("test_size", 0.25))}, random_state={int(dataset.get("seed", 42))}, stratify=y)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

backend = AerSimulator()
sampler = BackendSamplerV2(backend=backend, options={{"default_shots": {max(32, int(execution.get("shots", 128)))}}})
feature_map = {feature_map}(feature_dimension={max(1, int(circuit.get("num_qubits", 2)))}, reps=1)
ansatz = RealAmplitudes(num_qubits={max(1, int(circuit.get("num_qubits", 2)))}, reps={max(1, int(circuit.get("reps", 2)))})
classifier = VQC(feature_map=feature_map, ansatz=ansatz, optimizer={optimizer_name}(maxiter={max(1, int(optimizer.get("maxiter", 20)))}), sampler=sampler)
classifier.fit(X_train, y_train)
predictions = classifier.predict(X_test)
print("Test accuracy:", accuracy_score(y_test, predictions))
"""

    Path(out_path).write_text(code, encoding="utf-8")
    return str(out_path)
