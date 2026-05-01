from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import os
import pandas as pd

from runner import run_pipeline

app = Flask(__name__)
CORS(app)


def infer_label_column(columns):
    """
    Detect likely label column from uploaded or built-in dataset.
    """
    candidates = [
        "label",
        "class",
        "target",
        "y",
        "outcome",
        "species",
        "result",
        "prediction"
    ]

    lower_map = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:
        if candidate in lower_map:
            return lower_map[candidate]

    return columns[-1] if columns else None


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "QML DataFlow Studio backend is running",
        "status": "ok"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    })


@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload CSV dataset.
    Returns:
    - path
    - columns
    - inferred label
    - inferred feature columns
    - dataset summary
    - preview
    """
    upload_dir = os.path.join(
        os.path.dirname(__file__),
        "uploads"
    )

    os.makedirs(upload_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({
            "error": "No file part"
        }), 400

    file = request.files["file"]

    if not file.filename or not file.filename.lower().endswith(".csv"):
        return jsonify({
            "error": "Please upload a .csv file"
        }), 400

    destination = os.path.join(upload_dir, file.filename)
    file.save(destination)

    try:
        df = pd.read_csv(destination)
    except Exception as e:
        return jsonify({
            "error": f"Failed to read CSV: {e}"
        }), 400

    columns = df.columns.tolist()
    label_column = infer_label_column(columns)
    feature_columns = [
        col for col in columns
        if col != label_column
    ]

    preview_rows = min(len(df), 5)

    return jsonify({
        "ok": True,
        "path": f"uploads/{file.filename}",
        "columns": columns,
        "label_column": label_column,
        "feature_columns": feature_columns,
        "dataset_summary": {
            "dataset_type": "uploaded_csv",
            "rows": int(len(df)),
            "columns": len(columns),
            "label_column": label_column,
            "feature_columns": feature_columns
        },
        "preview": df.head(preview_rows).to_dict(orient="records")
    })


@app.route("/run", methods=["POST"])
def run():
    """
    Run pipeline and return dashboard-ready metrics.
    """
    try:
        spec = request.get_json(force=True)

        output = run_pipeline(spec)

        if isinstance(output, dict) and "status" not in output:
            output["status"] = "ok"

        return jsonify(output)

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
    Return predefined dataset configuration.
    """
    try:
        dataset_configs = {
            "diabetes": {
                "path": "datasets/diabetes.csv",
                "label_column": "Outcome",
                "feature_columns": [
                    "Pregnancies",
                    "Glucose",
                    "BloodPressure",
                    "BMI",
                    "Age"
                ],
                "description": "Diabetes prediction dataset"
            },
            "iris": {
                "path": "datasets/iris.csv",
                "label_column": "species",
                "feature_columns": [
                    "sepal_length",
                    "sepal_width",
                    "petal_length",
                    "petal_width"
                ],
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
            return jsonify({
                "error": f"Unknown dataset: {dataset_name}"
            }), 400

        config = dataset_configs[dataset_name]

        dataset_path = os.path.join(
            os.path.dirname(__file__),
            config["path"]
        )

        if not os.path.exists(dataset_path):
            return jsonify({
                "error": f"Dataset file not found: {config['path']}"
            }), 404

        df = pd.read_csv(dataset_path)
        columns = df.columns.tolist()
        preview_rows = min(len(df), 5)

        return jsonify({
            "ok": True,
            "name": dataset_name,
            "path": config["path"],
            "label_column": config["label_column"],
            "feature_columns": config["feature_columns"],
            "columns": columns,
            "description": config["description"],
            "dataset_summary": {
                "dataset_type": dataset_name,
                "rows": int(len(df)),
                "columns": len(columns),
                "label_column": config["label_column"],
                "feature_columns": config["feature_columns"]
            },
            "preview": df.head(preview_rows).to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to load dataset: {e}",
            "trace": traceback.format_exc()
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )