import numpy as np
from qiskit import QuantumCircuit

class Encoder:
    def __init__(self, n_qubits):
        self.n_qubits = n_qubits

    def encode(self, features):
        circuit = QuantumCircuit(self.n_qubits)
        normalized_features = self.normalize(features)
        for i in range(min(len(normalized_features), self.n_qubits)):
            circuit.ry(normalized_features[i], i)
        return circuit

    def normalize(self, features):
        features = np.array(features, dtype=float)
        mins = features.min(axis=0)
        maxs = features.max(axis=0)
        rng = (maxs - mins)
        rng[rng == 0] = 1.0
        normalized = (features - mins) / rng
        return normalized * np.pi