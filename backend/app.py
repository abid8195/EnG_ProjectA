# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os
import pandas as pd

# Classical ML pipeline (always available)
from runner import run_pipeline

# Kipu Quantum executor (requires qhub-quantum + qiskit to actually run)
from kipu_executor import get_kipu_backends, run_kipu_circuit

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload():
    """
    Save a CSV into backend/uploads and return its path and columns preview.
    """
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    dest = os.path.join(UPLOAD_DIR, f.filename)
    f.save(dest)

    try:
        df = pd.read_csv(dest)
    except Exception as e:
        return jsonify({"error": f"Failed to read CSV: {e}"}), 400

    cols = df.columns.tolist()
    preview_rows = min(len(df), 5)
    return jsonify({
        "ok": True,
        "path": f"uploads/{f.filename}",
        "columns": cols,
        "preview": df.head(preview_rows).to_dict(orient="records")
    })


@app.route("/run", methods=["POST"])
def run():
    """
    Run the classical ML pipeline (LogisticRegression).
    """
    try:
        spec = request.get_json(force=True)
        out = run_pipeline(spec)
        out["status"] = "ok"
        return jsonify(out)
    except ImportError as e:
        return jsonify({
            "status": "error",
            "error": "Qiskit packages missing",
            "detail": str(e),
            "trace": traceback.format_exc()
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# ---------------------------------------------------------------------------
# Kipu Quantum endpoints
# ---------------------------------------------------------------------------

@app.route("/kipu/backends", methods=["GET"])
def kipu_backends():
    """
    List available Kipu Quantum backends (simulators + real hardware).

    Query params:
        token  (str, required)  – KQH personal access token

    Returns:
        { "ok": true, "backends": [ {name, type, num_qubits, operational, description} ] }
    """
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"error": "token query parameter is required"}), 400

    try:
        backends = get_kipu_backends(token)
        return jsonify({"ok": True, "backends": backends})

    except ImportError as e:
        return jsonify({
            "error": "qhub-quantum SDK not installed",
            "detail": str(e),
            "hint":   "Run: pip install qhub-quantum"
        }), 500

    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 401 if "auth" in str(e).lower() else 400

    except Exception as e:
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/kipu/run", methods=["POST"])
def kipu_run():
    """
    Submit and execute a quantum circuit on a Kipu backend.

    JSON body:
        {
          "token":        str,            required
          "backend_name": str,            required – e.g. "aer_simulator"
          "circuit_spec": {               optional – defaults to Bell circuit
            "num_qubits":  2,
            "gates":       [{"gate": "h", "qubits": [0]}, ...],
            "measure_all": true
          },
          "shots": 1024                  optional
        }

    Returns:
        { "status": "ok", "job_id": ..., "backend": ..., "shots": ...,
          "counts": {...}, "time_taken": ..., "circuit": "<ascii diagram>" }
    """
    body = request.get_json(force=True) or {}

    token        = body.get("token", "").strip()
    backend_name = body.get("backend_name", "").strip()
    circuit_spec = body.get("circuit_spec", {})
    shots        = int(body.get("shots", 1024))

    if not token:
        return jsonify({"error": "token is required"}), 400
    if not backend_name:
        return jsonify({"error": "backend_name is required"}), 400
    if shots < 1 or shots > 100_000:
        return jsonify({"error": "shots must be between 1 and 100 000"}), 400

    try:
        result = run_kipu_circuit(
            token=token,
            backend_name=backend_name,
            circuit_spec=circuit_spec,
            shots=shots,
        )
        return jsonify(result)

    except ImportError as e:
        return jsonify({
            "error": "Required packages not installed",
            "detail": str(e),
            "hint":   "Run: pip install qhub-quantum qiskit"
        }), 500

    except (ValueError, RuntimeError) as e:
        status_code = 401 if "auth" in str(e).lower() else 400
        return jsonify({"error": str(e)}), status_code

    except Exception as e:
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# ---------------------------------------------------------------------------
# Predefined datasets
# ---------------------------------------------------------------------------

@app.route("/dataset/<dataset_name>", methods=["GET"])
def get_dataset(dataset_name):
    """
    Get predefined dataset information.
    """
    try:
        dataset_configs = {
            "diabetes": {
                "path": "datasets/diabetes.csv",
                "label_column": "outcome",
                "feature_columns": ["pregnancies", "glucose", "bloodpressure", "bmi", "age"],
                "description": "Diabetes prediction dataset"
            },
            "iris": {
                "path": "datasets/iris.csv",
                "label_column": "species",
                "feature_columns": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
                "description": "Iris flower classification dataset"
            },
            "realestate": {
                "path": "datasets/realestate.csv",
                "label_column": "price_high",
                "feature_columns": ["size", "bedrooms", "bathrooms", "age", "location_score"],
                "description": "Real estate price prediction dataset"
            },
            "heart_disease": {
                "path": "datasets/heart_disease.csv",
                "label_column": "heart_disease",
                "feature_columns": ["age", "cholesterol", "blood_pressure", "max_heart_rate", "blood_sugar", "chest_pain_type"],
                "description": "Heart disease binary classification dataset"
            }
        }

        if dataset_name not in dataset_configs:
            return jsonify({"error": f"Unknown dataset: {dataset_name}"}), 400

        config = dataset_configs[dataset_name]
        dataset_path = os.path.join(os.path.dirname(__file__), config["path"])

        if not os.path.exists(dataset_path):
            return jsonify({"error": f"Dataset file not found: {config['path']}"}), 404

        df = pd.read_csv(dataset_path)
        cols = df.columns.tolist()
        preview_rows = min(len(df), 5)

        return jsonify({
            "ok": True,
            "name": dataset_name,
            "path": config["path"],
            "label_column": config["label_column"],
            "feature_columns": config["feature_columns"],
            "columns": cols,
            "description": config["description"],
            "preview": df.head(preview_rows).to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to load dataset: {e}",
            "trace": traceback.format_exc()
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)