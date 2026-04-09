import numpy as np
from typing import Dict, Any


def compute_accuracy(predictions: np.ndarray, labels: np.ndarray) -> float:
    predictions = np.array(predictions)
    labels      = np.array(labels)
    if len(labels) == 0:
        return 0.0
    return float(np.sum(predictions == labels) / len(labels))


def expectation_z(circuit, n_qubits: int) -> np.ndarray:
    try:
        from qiskit import Aer
        from qiskit import transpile

        backend    = Aer.get_backend('statevector_simulator')
        transpiled = transpile(circuit, backend)
        job        = backend.run(transpiled)
        state      = np.array(job.result().get_statevector())
    except Exception:
        return np.zeros(n_qubits)

    exp_vals = np.zeros(n_qubits)
    for q in range(n_qubits):
        for idx, amp in enumerate(state):
            prob = abs(amp) ** 2
            bit  = (idx >> q) & 1
            exp_vals[q] += prob * (1.0 if bit == 0 else -1.0)

    return exp_vals


_VALID_ANSATZ      = ('ry', 'rz', 'rx', 'rxyz')
_VALID_ENTANGLE    = ('linear', 'circular', 'full')
_VALID_ENCODING    = ('angle', 'amplitude', 'basis', 'zz')


def validate_pipeline_config(config: Dict[str, Any]):
    n_qubits = config.get('n_qubits', 4)
    if not isinstance(n_qubits, int) or n_qubits < 1:
        raise ValueError(f"n_qubits must be a positive integer, got: {n_qubits!r}")

    layers = config.get('layers', 2)
    if not isinstance(layers, int) or layers < 1:
        raise ValueError(f"layers must be a positive integer, got: {layers!r}")

    ansatz = config.get('ansatz', 'ry')
    if ansatz not in _VALID_ANSATZ:
        raise ValueError(f"ansatz='{ansatz}' not recognised. Valid: {_VALID_ANSATZ}")

    entanglement = config.get('entanglement', 'linear')
    if entanglement not in _VALID_ENTANGLE:
        raise ValueError(
            f"entanglement='{entanglement}' not recognised. Valid: {_VALID_ENTANGLE}"
        )

    encoding_type = config.get('encoding_type', 'angle')
    if encoding_type not in _VALID_ENCODING:
        raise ValueError(
            f"encoding_type='{encoding_type}' not recognised. Valid: {_VALID_ENCODING}"
        )


def confusion_matrix_simple(predictions: np.ndarray,
                             labels: np.ndarray,
                             n_classes: int = None) -> np.ndarray:

    predictions = np.array(predictions, dtype=int)
    labels      = np.array(labels,      dtype=int)

    if n_classes is None:
        n_classes = int(max(labels.max(), predictions.max())) + 1

    cm = np.zeros((n_classes, n_classes), dtype=int)
    for true, pred in zip(labels, predictions):
        cm[true][pred] += 1
    return cm



def flatten_counts(counts: dict, n_qubits: int) -> np.ndarray:
    dim   = 2 ** n_qubits
    probs = np.zeros(dim)
    total = sum(counts.values())

    for bitstring, count in counts.items():
        idx        = int(bitstring[::-1], 2)
        if idx < dim:
            probs[idx] = count / total

    return probs
