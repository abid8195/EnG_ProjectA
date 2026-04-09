import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

SUPPORTED_ANSATZ      = ('ry', 'rz', 'rx', 'rxyz')
SUPPORTED_ENTANGLE    = ('linear', 'circular', 'full')


class VariationalCircuit:
    def __init__(self,
                 n_qubits: int,
                 layers: int,
                 ansatz: str = 'ry',
                 entanglement: str = 'linear'):

        if ansatz not in SUPPORTED_ANSATZ:
            raise ValueError(f"ansatz='{ansatz}' unknown. Choose from {SUPPORTED_ANSATZ}")
        if entanglement not in SUPPORTED_ENTANGLE:
            raise ValueError(f"entanglement='{entanglement}' unknown. Choose from {SUPPORTED_ENTANGLE}")

        self.n_qubits     = n_qubits
        self.layers       = layers
        self.ansatz       = ansatz
        self.entanglement = entanglement
        self.params       = self._initialize_parameters()

    def _initialize_parameters(self) -> list:
        multiplier = 3 if self.ansatz == 'rxyz' else 1
        count      = self.n_qubits * self.layers * multiplier
        return [Parameter(f'θ_{i}') for i in range(count)]

    def _apply_rotation_layer(self, qc: QuantumCircuit, layer: int, param_idx: int) -> int:
        for qubit in range(self.n_qubits):
            if self.ansatz == 'ry':
                qc.ry(self.params[param_idx], qubit)
                param_idx += 1
            elif self.ansatz == 'rz':
                qc.rz(self.params[param_idx], qubit)
                param_idx += 1
            elif self.ansatz == 'rx':
                qc.rx(self.params[param_idx], qubit)
                param_idx += 1
            elif self.ansatz == 'rxyz':
                qc.rx(self.params[param_idx],     qubit)
                qc.ry(self.params[param_idx + 1], qubit)
                qc.rz(self.params[param_idx + 2], qubit)
                param_idx += 3
        return param_idx

    def _apply_entanglement_layer(self, qc: QuantumCircuit):
        n = self.n_qubits

        if self.entanglement == 'linear':
            for q in range(n - 1):
                qc.cz(q, q + 1)

        elif self.entanglement == 'circular':
            for q in range(n - 1):
                qc.cz(q, q + 1)
            if n > 2:
                qc.cz(n - 1, 0)

        elif self.entanglement == 'full':
            for q1 in range(n):
                for q2 in range(q1 + 1, n):
                    qc.cz(q1, q2)

    def build_circuit(self) -> QuantumCircuit:
        qc        = QuantumCircuit(self.n_qubits)
        param_idx = 0

        for layer in range(self.layers):
            param_idx = self._apply_rotation_layer(qc, layer, param_idx)
            self._apply_entanglement_layer(qc)
            qc.barrier()

        return qc

    def get_parameter_values(self, values: list) -> dict:
        if len(values) != len(self.params):
            raise ValueError(
                f"Expected {len(self.params)} parameter values, got {len(values)}."
            )
        return {self.params[i]: values[i] for i in range(len(values))}

    def param_count(self) -> int:
        return len(self.params)

    def __repr__(self):
        return (f"VariationalCircuit(n_qubits={self.n_qubits}, layers={self.layers}, "
                f"ansatz='{self.ansatz}', entanglement='{self.entanglement}', "
                f"params={self.param_count()})")
