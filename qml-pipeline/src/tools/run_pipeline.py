import json
import sys
import math
import argparse
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from qiskit import QuantumCircuit, Aer, transpile


SUPPORTED_ANSATZ   = ('ry', 'rz', 'rx', 'rxyz')
SUPPORTED_ENTANGLE = ('linear', 'circular', 'full')
SUPPORTED_ENCODING = ('angle', 'amplitude', 'basis', 'zz')


def load_model(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def infer_pipeline(model: dict) -> dict:
    defaults = {
        'encoder':      'angle',
        'ansatz':       'ry',
        'entanglement': 'linear',
        'layers':       2,
    }

    if isinstance(model, dict) and 'nodes' in model and 'edges' in model:
        nodes = {n['type']: n for n in model['nodes']}

        enc_node  = nodes.get('encoder', {}).get('params', {})
        circ_node = nodes.get('circuit', {}).get('params', {})

        return {
            'encoder':      enc_node.get('type',         defaults['encoder']),
            'ansatz':       circ_node.get('ansatz',      defaults['ansatz']),
            'entanglement': circ_node.get('entanglement', defaults['entanglement']),
            'layers':       int(circ_node.get('layers',  defaults['layers']) or 2),
        }

    if isinstance(model, dict) and 'drawflow' in model:
        home     = model['drawflow'].get('Home', {})
        enc_cfg  = {}
        circ_cfg = {}

        for k, node in home.items():
            t      = (node.get('data') or {}).get('type') or (node.get('name') or '').lower()
            params = (node.get('data') or {}).get('params') or {}
            if 'encoder' in t:
                enc_cfg = params
            if 'circuit' in t:
                circ_cfg = params

        return {
            'encoder':      enc_cfg.get('type',          defaults['encoder']),
            'ansatz':       circ_cfg.get('ansatz',       defaults['ansatz']),
            'entanglement': circ_cfg.get('entanglement', defaults['entanglement']),
            'layers':       int(circ_cfg.get('layers',   defaults['layers']) or 2),
        }

    return defaults


def normalize_features(X: np.ndarray) -> np.ndarray:
    X    = np.array(X, dtype=float)
    mins = X.min(axis=0)
    maxs = X.max(axis=0)
    rng  = maxs - mins
    rng[rng == 0] = 1.0
    return (X - mins) / rng * math.pi


def build_encoding_circuit(x: np.ndarray,
                            n_qubits: int,
                            encoding_type: str = 'angle') -> QuantumCircuit:
                              
    qc = QuantumCircuit(n_qubits)
    n  = min(len(x), n_qubits)

    if encoding_type == 'angle':
        for i in range(n):
            qc.ry(float(x[i]), i)

    elif encoding_type == 'amplitude':
        dim    = 2 ** n_qubits
        padded = np.zeros(dim)
        padded[:min(len(x), dim)] = x[:min(len(x), dim)]
        norm   = np.linalg.norm(padded)
        padded = padded / norm if norm > 1e-12 else np.eye(dim)[0]
        qc.initialize(padded.tolist(), list(range(n_qubits)))

    elif encoding_type == 'basis':
        for i in range(n):
            if x[i] != 0:
                qc.x(i)

    elif encoding_type == 'zz':
        for i in range(n):
            qc.ry(float(x[i]), i)
        for i in range(n):
            for j in range(i + 1, n):
                qc.crz(2.0 * float(x[i]) * float(x[j]), i, j)

    else:
        raise ValueError(f"Unknown encoding_type='{encoding_type}'. "
                         f"Choose from {SUPPORTED_ENCODING}")
    return qc


def build_variational_circuit(params: np.ndarray,
                               n_qubits: int,
                               layers: int,
                               ansatz: str = 'ry',
                               entanglement: str = 'linear') -> QuantumCircuit:
                                 
    if ansatz not in SUPPORTED_ANSATZ:
        raise ValueError(f"ansatz='{ansatz}' not in {SUPPORTED_ANSATZ}")
    if entanglement not in SUPPORTED_ENTANGLE:
        raise ValueError(f"entanglement='{entanglement}' not in {SUPPORTED_ENTANGLE}")

    qc  = QuantumCircuit(n_qubits)
    idx = 0

    for _ in range(layers):
        for q in range(n_qubits):
            a = float(params[idx])
            if ansatz == 'ry':
                qc.ry(a, q); idx += 1
            elif ansatz == 'rz':
                qc.rz(a, q); idx += 1
            elif ansatz == 'rx':
                qc.rx(a, q); idx += 1
            elif ansatz == 'rxyz':
                qc.rx(float(params[idx]),     q)
                qc.ry(float(params[idx + 1]), q)
                qc.rz(float(params[idx + 2]), q)
                idx += 3

        if entanglement == 'linear':
            for q in range(n_qubits - 1):
                qc.cz(q, q + 1)
        elif entanglement == 'circular':
            for q in range(n_qubits - 1):
                qc.cz(q, q + 1)
            if n_qubits > 2:
                qc.cz(n_qubits - 1, 0)
        elif entanglement == 'full':
            for q1 in range(n_qubits):
                for q2 in range(q1 + 1, n_qubits):
                    qc.cz(q1, q2)

        qc.barrier()

    return qc

def circuit_feature_vector(x: np.ndarray,
                            params: np.ndarray,
                            n_qubits: int,
                            layers: int,
                            ansatz: str,
                            entanglement: str,
                            encoding_type: str,
                            backend) -> np.ndarray:
    
    enc = build_encoding_circuit(x, n_qubits, encoding_type)
    var = build_variational_circuit(params, n_qubits, layers, ansatz, entanglement)
    qc  = enc.compose(var)
    qc.save_statevector()
    job    = backend.run(transpile(qc, backend))
    state  = np.array(job.result().get_statevector())

    feats = []
    for q in range(n_qubits):
        exp = sum(
            (abs(amp) ** 2) * (1.0 if ((i >> q) & 1) == 0 else -1.0)
            for i, amp in enumerate(state)
        )
        feats.append(exp)
    return np.array(feats)
                              

def param_count(n_qubits: int, layers: int, ansatz: str) -> int:
    mult = 3 if ansatz == 'rxyz' else 1
    return n_qubits * layers * mult


def evaluate_pipeline(conf: dict, tries: int = 10) -> dict:
    iris    = load_iris()
    Xn      = normalize_features(iris.data)
    y       = iris.target

    n_qubits     = min(Xn.shape[1], 4)
    layers       = int(conf.get('layers', 2))
    ansatz       = conf.get('ansatz', 'ry')
    entanglement = conf.get('entanglement', 'linear')
    encoding     = conf.get('encoder', 'angle')
    p_dim        = param_count(n_qubits, layers, ansatz)

    backend      = Aer.get_backend('aer_simulator')

    X_train, X_test, y_train, y_test = train_test_split(
        Xn, y, test_size=0.3, random_state=42, stratify=y
    )

    best = {'acc': 0.0, 'params': None}

    for t in range(tries):
        params = np.random.uniform(0, 2 * math.pi, size=(p_dim,))
        kwargs = dict(n_qubits=n_qubits, layers=layers,
                      ansatz=ansatz, entanglement=entanglement,
                      encoding_type=encoding, backend=backend)
        try:
            X_tr_f = np.vstack([circuit_feature_vector(x, params, **kwargs) for x in X_train])
            X_te_f = np.vstack([circuit_feature_vector(x, params, **kwargs) for x in X_test])
        except Exception as e:
            print(f"  [try {t+1}] circuit error: {e}")
            continue

        clf = LogisticRegression(max_iter=300, multi_class='multinomial', solver='lbfgs')
        try:
            clf.fit(X_tr_f, y_train)
            acc = clf.score(X_te_f, y_test)
        except Exception:
            acc = 0.0

        print(f"  [try {t+1}/{tries}]  acc={acc:.4f}  "
              f"ansatz={ansatz}  entangle={entanglement}  enc={encoding}")

        if acc > best['acc']:
            best = {'acc': acc, 'params': params}

    return {
        'best_accuracy': float(best['acc']),
        'param_dim':     int(p_dim),
        'n_qubits':      int(n_qubits),
        'layers':        int(layers),
        'ansatz':        ansatz,
        'entanglement':  entanglement,
        'encoding_type': encoding,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run QML pipeline validation on Iris dataset."
    )
    parser.add_argument('model_path', help='Path to pipeline_model.json')
    parser.add_argument('--tries', type=int, default=10,
                        help='Number of random parameter initialisations (default: 10)')
    args = parser.parse_args()

    model = load_model(args.model_path)
    conf  = infer_pipeline(model)

    print("Pipeline config inferred:", conf)
    print(f"Running {args.tries} random-parameter trials on Iris …\n")

    out = evaluate_pipeline(conf, tries=args.tries)

    print("\n── Results ──────────────────────────────")
    for k, v in out.items():
        print(f"  {k:<20}: {v}")


if __name__ == "__main__":
    main()
