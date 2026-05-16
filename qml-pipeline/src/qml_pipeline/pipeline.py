import json
import numpy as np
from qiskit import QuantumCircuit

from qml_pipeline.encoder       import Encoder
from qml_pipeline.variational   import VariationalCircuit
from qml_pipeline.utils         import (compute_accuracy,
                                        expectation_z,
                                        validate_pipeline_config)
from qml_pipeline.model_io      import load_model, save_model


class Pipeline:
    def __init__(self, model: dict):
        validate_pipeline_config(model)
        self.model = model

        self.n_qubits      = int(model.get('n_qubits',      4))
        self.layers        = int(model.get('layers',         2))
        self.ansatz        = model.get('ansatz',        'ry')
        self.entanglement  = model.get('entanglement',  'linear')
        self.encoding_type = model.get('encoding_type', 'angle')

        self.encoder    = Encoder(self.n_qubits, self.encoding_type)
        self.var_circuit = VariationalCircuit(
            self.n_qubits,
            self.layers,
            self.ansatz,
            self.entanglement
        )

        self._params = np.random.uniform(
            0, 2 * np.pi, size=(self.var_circuit.param_count(),)
        )


    @property
    def params(self) -> np.ndarray:
        return self._params

    @params.setter
    def params(self, values):
        values = np.array(values, dtype=float)
        if values.shape != self._params.shape:
            raise ValueError(
                f"Expected {self._params.shape[0]} parameters, got {values.shape[0]}."
            )
        self._params = values

    
    def run(self, data: np.ndarray) -> np.ndarray:
        data    = np.atleast_2d(data)
        results = []

        param_bindings = self.var_circuit.get_parameter_values(self._params.tolist())

        for sample in data:
            enc_qc = self.encoder.encode(sample)
            var_qc = self.var_circuit.build_circuit().assign_parameters(param_bindings)
            full_qc = enc_qc.compose(var_qc)
            exp_vals = expectation_z(full_qc, self.n_qubits)
            results.append(exp_vals)

        return np.array(results)


    def evaluate(self, results: np.ndarray, labels: np.ndarray) -> dict:
        predictions = np.argmax(results, axis=1) % len(np.unique(labels))
        acc         = compute_accuracy(predictions, labels)

        return {
            'accuracy':  float(acc),
            'n_samples': int(len(labels)),
            'n_correct': int(round(acc * len(labels))),
        }


def load_pipeline_model(path: str) -> dict:
    return load_model(path)


def save_pipeline_results(results: dict, path: str):
    save_model(path, results)


def preprocess_data(data: np.ndarray) -> np.ndarray:
    data = np.array(data, dtype=float)

    col_means = np.nanmean(data, axis=0)
    nan_mask  = np.isnan(data)
    data[nan_mask] = np.take(col_means, np.where(nan_mask)[1])

    mins = data.min(axis=0)
    maxs = data.max(axis=0)
    rng  = maxs - mins
    rng[rng == 0] = 1.0
    return (data - mins) / rng


def postprocess_results(results: np.ndarray) -> np.ndarray:
    return np.argmax(results, axis=1)
