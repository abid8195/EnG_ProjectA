import numpy as np
from qiskit import QuantumCircuit
from qiskit.extensions import Initialize

SUPPORTED_ENCODINGS = ('angle', 'amplitude', 'basis', 'zz')

class Encoder:

    def __init__(self, n_qubits: int, encoding_type: str = 'angle'):
        if encoding_type not in SUPPORTED_ENCODINGS:
            raise ValueError(
                f"encoding_type='{encoding_type}' unknown. Choose from {SUPPORTED_ENCODINGS}"
            )
        self.n_qubits      = n_qubits
        self.encoding_type = encoding_type


    def encode(self, features) -> QuantumCircuit:

        features = np.array(features, dtype=float)

        if self.encoding_type == 'angle':
            return self._angle_encode(features)
        elif self.encoding_type == 'amplitude':
            return self._amplitude_encode(features)
        elif self.encoding_type == 'basis':
            return self._basis_encode(features)
        elif self.encoding_type == 'zz':
            return self._zz_encode(features)

    def _angle_encode(self, features: np.ndarray) -> QuantumCircuit:

        qc     = QuantumCircuit(self.n_qubits)
        scaled = self.normalize(features)
        for i in range(min(len(scaled), self.n_qubits)):
            qc.ry(float(scaled[i]), i)
        return qc

    def _amplitude_encode(self, features: np.ndarray) -> QuantumCircuit:

        qc          = QuantumCircuit(self.n_qubits)
        state_dim   = 2 ** self.n_qubits

        padded = np.zeros(state_dim)
        n_take = min(len(features), state_dim)
        padded[:n_take] = features[:n_take]

        norm = np.linalg.norm(padded)
        if norm < 1e-12:
            padded[0] = 1.0
        else:
            padded = padded / norm

        qc.initialize(padded, list(range(self.n_qubits)))
        return qc

    def _basis_encode(self, features: np.ndarray) -> QuantumCircuit:

        qc = QuantumCircuit(self.n_qubits)
        for i in range(min(len(features), self.n_qubits)):
            if features[i] != 0:
                qc.x(i)
        return qc

    def _zz_encode(self, features: np.ndarray) -> QuantumCircuit:

        qc     = QuantumCircuit(self.n_qubits)
        scaled = self.normalize(features)
        n      = min(len(scaled), self.n_qubits)

        for i in range(n):
            qc.ry(float(scaled[i]), i)

        for i in range(n):
            for j in range(i + 1, n):
                angle = 2.0 * float(scaled[i]) * float(scaled[j])
                qc.crz(angle, i, j)

        return qc

    def normalize(self, features: np.ndarray) -> np.ndarray:
        """
        Min-max scales features to [0, π].
        Works on a 1-D array (single sample) or 2-D (batch of samples).
        """
        features = np.array(features, dtype=float)
        if features.ndim == 1:
            lo, hi = features.min(), features.max()
            rng    = hi - lo if (hi - lo) > 1e-12 else 1.0
            return (features - lo) / rng * np.pi

        mins = features.min(axis=0)
        maxs = features.max(axis=0)
        rng  = (maxs - mins)
        rng[rng == 0] = 1.0
        return (features - mins) / rng * np.pi

    def __repr__(self):
        return f"Encoder(n_qubits={self.n_qubits}, encoding_type='{self.encoding_type}')"
