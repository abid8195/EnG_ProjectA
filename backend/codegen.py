# backend/codegen.py
from pathlib import Path

def write_generated_run(spec: dict, out_path: str = None) -> str:
    """
    Generate simple Python code using classical ML (no Qiskit dependencies).
    """
    if out_path is None:
        project_root = Path(__file__).resolve().parents[1]
        out_path = project_root / "generated_run.py"

    ds  = spec.get("dataset", {})
    opt = spec.get("optimizer", {})

    # Generate simple classical ML code
    code = f"""# Auto-generated Classical ML Pipeline
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn import datasets

def load_data():
    np.random.seed({ds.get("seed", 42)})
    test_size = {ds.get("test_size", 0.2)}

    if "{ds.get("type", "synthetic-line")}" == "synthetic-line":
        X = 2 * np.random.random([{ds.get("num_samples", 20)}, {ds.get("num_features", 2)}]) - 1
        y = (np.sum(X, axis=1) >= 0).astype(int) * 2 - 1
        return train_test_split(X, y, test_size=test_size, random_state={ds.get("seed", 42)})
    elif "{ds.get("type", "synthetic-line")}" == "iris":
        iris = datasets.load_iris()
        X_all, y_all = iris.data, iris.target
        mask = np.isin(y_all, {ds.get("classes", [0, 1])})
        X = X_all[mask][:, {ds.get("features", [0, 1])}]
        y_raw = y_all[mask]
        y = (y_raw == max({ds.get("classes", [0, 1])})).astype(int) * 2 - 1
        return train_test_split(X, y, test_size=test_size, random_state={ds.get("seed", 42)})
    else:
        raise ValueError("Unknown dataset type: {ds.get("type", "synthetic-line")}")

def main():
    Xtr, Xte, ytr, yte = load_data()
    
    # Preprocess data
    scaler = StandardScaler()
    Xtr_scaled = scaler.fit_transform(Xtr)
    Xte_scaled = scaler.transform(Xte)
    
    # Train classical classifier
    clf = LogisticRegression(max_iter={opt.get("maxiter", 100)}, random_state=42)
    clf.fit(Xtr_scaled, ytr)
    
    # Evaluate
    train_acc = clf.score(Xtr_scaled, ytr)
    test_acc = clf.score(Xte_scaled, yte)
    
    print(f"Training accuracy: {{train_acc:.4f}}")
    print(f"Test accuracy: {{test_acc:.4f}}")
    print(f"Predictions: {{clf.predict(Xte_scaled)[:10]}}")

if __name__ == "__main__":
    main()
"""

    Path(out_path).write_text(code)
    return str(out_path)