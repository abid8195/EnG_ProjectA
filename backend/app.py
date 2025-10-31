# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os
import pandas as pd

# IMPORTANT: we use runner.py which REQUIRES qiskit packages.
from runner import run_pipeline  # raises ImportError with a clear message if Qiskit missing

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
    import os, pandas as pd
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
        "path": f"uploads/{f.filename}",  # relative to backend folder (runner handles this)
        "columns": cols,
        "preview": df.head(preview_rows).to_dict(orient="records")
    })

@app.route("/run", methods=["POST"])
def run():
    """
    Run the QML pipeline. NO classical fallback here.
    If Qiskit is missing, you get a 500 with an explicit message.
    """
    try:
        spec = request.get_json(force=True)
        out = run_pipeline(spec)
        # Make it explicit that this is the quantum path (no 'note' key anymore)
        out["status"] = "ok"
        return jsonify(out)
    except ImportError as e:
        # Surface exactly which modules are missing
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
            }
        }
        
        if dataset_name not in dataset_configs:
            return jsonify({"error": f"Unknown dataset: {dataset_name}"}), 400
            
        config = dataset_configs[dataset_name]
        dataset_path = os.path.join(os.path.dirname(__file__), config["path"])
        
        if not os.path.exists(dataset_path):
            return jsonify({"error": f"Dataset file not found: {config['path']}"}), 404
            
        # Read the dataset to get columns and preview
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
    # Bind to all interfaces so your frontend at http://localhost:8000 can reach it.
    app.run(host="0.0.0.0", port=5000, debug=True)