from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os
import pandas as pd

from runner import run_pipeline

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
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    dest = os.path.join(upload_dir, f.filename)
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
    Run the pipeline and return training metrics for the dashboard.
    """
    try:
        spec = request.get_json(force=True)
        out = run_pipeline(spec)

        if isinstance(out, dict) and "status" not in out:
            out["status"] = "ok"

        return jsonify(out)

    except ValueError as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 400

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
                "label_column": "Outcome",
                "feature_columns": ["Pregnancies", "Glucose", "BloodPressure", "BMI", "Age"],
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
                "label_column": "Y house price of unit area",
                "feature_columns": [
                    "X1 transaction date",
                    "X2 house age",
                    "X3 distance to the nearest MRT station",
                    "X4 number of convenience stores",
                    "X5 latitude"
                ],
                "description": "Real estate price dataset"
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