# ...new file...
"""
Minimal runner that reads a pipeline model JSON (drawflow-export or pipeline_model.json)
and runs a lightweight Qiskit-based feature transform + classical classifier on the Iris dataset.

Usage:
  python tools/run_pipeline.py path/to/pipeline_model.json

Dependencies:
  pip install qiskit scikit-learn numpy

Notes:
  - This runner is intentionally small: it constructs angle-encoding + simple variational
    circuit, evaluates expectation values as features and trains a sklearn LogisticRegression
    to validate end-to-end behavior on Iris.
  - It does not require qiskit-machine-learning; it's a lightweight validation harness.
"""
import json
import sys
import math
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from qiskit import QuantumCircuit, Aer
from qiskit.opflow import StateFn, Z, AerPauliExpectation, PauliOp

def load_model(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def infer_pipeline(model):
    # accept either our pipeline schema or drawflow export
    if isinstance(model, dict) and model.get('nodes') and model.get('edges') is not None:
        # pipeline schema style
        nodes = { n['type'] : n for n in model['nodes'] }
        encoder = nodes.get('encoder', {}).get('params', {}).get('type', 'angle')
        circuit = nodes.get('circuit', {}).get('params', {})
        ansatz = circuit.get('ansatz','ry')
        layers = int(circuit.get('layers', 2) or 2)
        return {'encoder': encoder, 'ansatz': ansatz, 'layers': layers}
    # drawflow export shape
    if model.get('drawflow'):
        # find nodes
        home = model['drawflow'].get('Home', {})
        enc = None; circ = None
        for k, n in home.items():
            t = (n.get('data') or {}).get('type') or (n.get('name') or '').lower()
            params = (n.get('data') or {}).get('params') or {}
            if t == 'encoder' or 'encoder' in (n.get('name') or '').lower():
                enc = params.get('type','angle')
            if t == 'circuit' or 'circuit' in (n.get('name') or '').lower():
                circ = params
        ansatz = (circ or {}).get('ansatz','ry')
        layers = int((circ or {}).get('layers',2) or 2)
        return {'encoder': enc or 'angle', 'ansatz': ansatz, 'layers': layers}
    # fallback defaults
    return {'encoder': 'angle', 'ansatz': 'ry', 'layers': 2}

# simple normalization -> [0, pi]
def normalize_features(X):
    X = np.array(X, dtype=float)
    mins = X.min(axis=0)
    maxs = X.max(axis=0)
    rng = (maxs - mins)
    rng[rng == 0] = 1.0
    Xn = (X - mins) / rng
    return Xn * math.pi

def build_encoding_circuit(x, n_qubits):
    qc = QuantumCircuit(n_qubits)
    for i in range(min(len(x), n_qubits)):
        qc.ry(float(x[i]), i)
    return qc

def build_variational_circuit(params, n_qubits, layers, ansatz='ry'):
    qc = QuantumCircuit(n_qubits)
    idx = 0
    for l in range(layers):
        for q in range(n_qubits):
            angle = float(params[idx]); idx += 1
            if ansatz == 'ry':
                qc.ry(angle, q)
            else:
                qc.rz(angle, q)
        for q in range(n_qubits - 1):
            qc.cz(q, q+1)
    return qc

def circuit_feature_vector(x, params, n_qubits, layers, ansatz, backend):
    # build encoding + variational and return expectation values of Z on each qubit
    enc = build_encoding_circuit(x, n_qubits)
    var = build_variational_circuit(params, n_qubits, layers, ansatz)
    qc = enc.compose(var)
    # use statevector simulator -> compute Z expectation via statevector
    sv_backend = backend
    job = sv_backend.run(qc.save_statevector())
    result = job.result()
    state = result.get_statevector(qc)
    # compute expectation of Z on each qubit
    vec = np.array(state)
    n = n_qubits
    feats = []
    for q in range(n):
        # build Z operator expectation via computational basis
        exp = 0.0
        dim = 2**n
        for idx_state, amp in enumerate(vec):
            prob = (abs(amp)**2)
            # bit value at position q (lsb=0)
            bit = (idx_state >> q) & 1
            val = 1.0 if bit == 0 else -1.0
            exp += val * prob
        feats.append(exp)
    return np.array(feats)

def evaluate_pipeline(conf, tries=25):
    iris = load_iris()
    X = iris.data
    y = iris.target
    # optionally restrict to first two classes for binary (easier), but keep multiclass using logistic regression's multinomial
    Xn = normalize_features(X)
    n_features = Xn.shape[1]
    n_qubits = min(n_features, 4)
    layers = int(conf.get('layers', 2))
    ansatz = conf.get('ansatz', 'ry')
    backend = Aer.get_backend('aer_simulator')
    # prepare search over random params
    best = {'acc': 0.0, 'params': None}
    # prepare train/test split indices (fixed)
    X_train, X_test, y_train, y_test = train_test_split(Xn, y, test_size=0.3, random_state=42, stratify=y)
    # Try random parameter initializations and for each compute features + classical classifier
    param_dim = n_qubits * layers
    for t in range(tries):
        params = np.random.uniform(0, 2*math.pi, size=(param_dim,))
        # compute circuit features for all training samples
        X_train_feats = []
        for x in X_train:
            v = circuit_feature_vector(x, params, n_qubits, layers, ansatz, backend)
            X_train_feats.append(v)
        X_test_feats = []
        for x in X_test:
            v = circuit_feature_vector(x, params, n_qubits, layers, ansatz, backend)
            X_test_feats.append(v)
        X_train_feats = np.vstack(X_train_feats)
        X_test_feats = np.vstack(X_test_feats)
        # simple classifier (logistic reg)
        clf = LogisticRegression(max_iter=200, multi_class='multinomial', solver='lbfgs')
        try:
            clf.fit(X_train_feats, y_train)
            acc = clf.score(X_test_feats, y_test)
        except Exception as e:
            acc = 0.0
        if acc > best['acc']:
            best = {'acc': acc, 'params': params}
    return { 'best_accuracy': best['acc'], 'param_dim': int(param_dim), 'n_qubits': int(n_qubits), 'layers': int(layers), 'ansatz': ansatz }

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/run_pipeline.py path/to/pipeline_model.json")
        sys.exit(1)
    path = sys.argv[1]
    model = load_model(path)
    conf = infer_pipeline(model)
    print("Pipeline config inferred:", conf)
    print("Running lightweight validation on Iris (this may take ~30s depending on tries/backend).")
    out = evaluate_pipeline(conf, tries=10)
    print("Result:", out)

if __name__ == "__main__":
    main()