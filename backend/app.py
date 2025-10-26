from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, traceback

# Optional deps for nicer CSV introspection
try:
    import pandas as pd
except Exception:
    pd = None

# Local runner/codegen
try:
    from runner import run_pipeline  # executes QML pipeline
except Exception as e:
    run_pipeline = None

try:
    from codegen import write_generated_run  # writes generated_run.py from spec
except Exception:
    write_generated_run = None

# ---------------- Flask basic setup ----------------
app = Flask(__name__)
CORS(app)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _default_spec():
    # Reasonable defaults aligned with the front-end 'spec' object
    return {
        "pipeline": "qml-classifier",
        "qnn": {"type": "estimator"},
        "dataset": {
            "type": "synthetic-line",   # fast fallback if user didn't upload CSV
            "num_samples": 24,
            "num_features": 2,
            "test_size": 0.2,
            "seed": 42
        },
        "encoder": {"type": "zzfeaturemap"},
        "circuit": {"type": "realamplitudes", "num_qubits": 2, "reps": 1},
        "optimizer": {"type": "cobyla", "maxiter": 15},
        "outputs": {"return_predictions": True, "return_generated_code": False}
    }


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if not file.filename.lower().endswith(".csv"):
            return jsonify({"error": "Invalid file type; only .csv"}), 400

        save_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(save_path)

        # Build response: columns, rows, preview (first 5 rows as list of dicts)
        columns = []
        rows = 0
        preview = []

        if pd is not None:
            try:
                df = pd.read_csv(save_path, nrows=1000)  # light sniff
                columns = df.columns.tolist()
                rows = int(len(df))
                preview = df.head(5).to_dict(orient="records")
            except Exception:
                # Fallback: basic csv sniff if pandas had trouble
                import csv
                with open(save_path, "r", newline="", encoding="utf-8") as f:
                    rdr = csv.reader(f)
                    first = next(rdr)
                    columns = [c.strip() for c in first]
                    for i, _ in enumerate(rdr, start=1):
                        if i <= 5:
                            # Build preview rows as dict of strings
                            pass
                    rows = i
        else:
            # Pure-stdlib fallback
            import csv
            with open(save_path, "r", newline="", encoding="utf-8") as f:
                rdr = csv.reader(f)
                first = next(rdr)
                columns = [c.strip() for c in first]
                for i, row in enumerate(rdr, start=1):
                    if i <= 5:
                        preview.append({columns[j]: row[j] if j < len(row) else "" for j in range(len(columns))})
                rows = i if 'i' in locals() else 0

        return jsonify({
            "ok": True,
            "path": os.path.relpath(save_path, APP_DIR).replace("\\", "/"),
            "columns": columns,
            "rows": rows,
            "preview": preview
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/run", methods=["POST"])
def run_route():
    try:
        incoming = request.get_json(silent=True) or {}
        spec = _default_spec()

        # Merge incoming spec shallowly; respect keys the UI sets
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(spec.get(k), dict):
                spec[k].update(v)
            else:
                spec[k] = v

        # If the user uploaded a CSV, ensure dataset.type is csv
        ds = spec.get("dataset", {})
        if ds.get("path"):
            ds["type"] = "csv"
            spec["dataset"] = ds

        # Cap heavy knobs so the demo stays quick
        cir = spec.get("circuit", {})
        cir["num_qubits"] = int(cir.get("num_qubits", 4))
        cir["num_qubits"] = max(1, min(cir["num_qubits"], 4))
        cir["reps"] = int(cir.get("reps", 1))
        spec["circuit"] = cir

        opt = spec.get("optimizer", {})
        opt["type"] = opt.get("type", "cobyla")
        opt["maxiter"] = max(1, min(int(opt.get("maxiter", 15)), 20))
        spec["optimizer"] = opt

        # Execute
        if run_pipeline is None:
            # Graceful fallback if qiskit libs are not installed
            return jsonify({
                "status": "ok",
                "warning": "Qiskit not installed in this environment; returning mock result.",
                "spec_echo": spec,
                "accuracy": 0.0,
                "n_train": 0,
                "n_test": 0,
            })

        result = run_pipeline(spec)

        # Optional: write generated_run.py if requested and codegen is available
        gen_code_path = None
        if spec.get("outputs", {}).get("return_generated_code") and write_generated_run:
            try:
                gen_code_path = write_generated_run(spec)
            except Exception:
                gen_code_path = None

        payload = {"status": "ok", **result}
        if gen_code_path:
            payload["generated_code_path"] = gen_code_path
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 400


@app.route("/", methods=["GET"])
def root():
    return jsonify({"ok": True, "msg": "Backend alive", "endpoints": ["/upload", "/run"]})


if __name__ == "__main__":
    # Bind to all interfaces so the front-end can hit http://localhost:5000 from a browser
    app.run(host="0.0.0.0", port=5000, debug=True)
