import numpy as np
from qiskit import QuantumCircuit, Aer, transpile
from qiskit.circuit import Parameter

class VariationalCircuit:
    def __init__(self, n_qubits, layers, ansatz='ry'):
        self.n_qubits = n_qubits
        self.layers = layers
        self.ansatz = ansatz
        self.params = self._initialize_parameters()

    def _initialize_parameters(self):
        return [Parameter(f'θ_{i}') for i in range(self.n_qubits * self.layers)]

    def build_circuit(self):
        qc = QuantumCircuit(self.n_qubits)
        param_idx = 0

        for layer in range(self.layers):
            for qubit in range(self.n_qubits):
                if self.ansatz == 'ry':
                    qc.ry(self.params[param_idx], qubit)
                elif self.ansatz == 'rz':
                    qc.rz(self.params[param_idx], qubit)
                param_idx += 1

            for qubit in range(self.n_qubits - 1):
                qc.cz(qubit, qubit + 1)

        return qc

    def evaluate(self, backend, shots=1024):
        qc = self.build_circuit()
        qc = transpile(qc, backend)
        job = backend.run(qc, shots=shots)
        result = job.result()
        counts = result.get_counts(qc)
        return counts

    def get_parameter_values(self, values):
        return {self.params[i]: values[i] for i in range(len(values))}