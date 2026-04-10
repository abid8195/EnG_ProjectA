from pathlib import Path
import traceback

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from dataset_catalog import DATASET_CONFIGS
from runners import get_runner, list_all_backends

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/upload", methods=["POST"])
def upload():
    """
    Save a CSV into uploads and return its path and columns preview.
    """
    upload_dir = Path(__file__).resolve().parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    dest = upload_dir / f.filename
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
        out = get_runner(spec).run(spec)

        if isinstance(out, dict) and "status" not in out:
            out["status"] = "ok"

        return jsonify(out)

    except ValueError as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 400

    except ImportError as e:
        return jsonify({
            "status": "error",
            "error": str(e)
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
        if dataset_name not in DATASET_CONFIGS:
            return jsonify({"error": f"Unknown dataset: {dataset_name}"}), 400

        config = DATASET_CONFIGS[dataset_name]
        dataset_path = Path(config["path"])

        if not dataset_path.exists():
            return jsonify({"error": f"Dataset file not found: {dataset_path.name}"}), 404

        df = pd.read_csv(dataset_path)
        cols = df.columns.tolist()
        preview_rows = min(len(df), 5)

        return jsonify({
            "ok": True,
            "name": dataset_name,
            "path": str(dataset_path.relative_to(Path(__file__).resolve().parent)).replace("\\", "/"),
            "label_column": config["label_column"],
            "feature_columns": config["feature_columns"],
            "columns": cols,
            "description": config["description"],
            "domain": config["domain"],
            "preview": df.head(preview_rows).to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to load dataset: {e}",
            "trace": traceback.format_exc()
        }), 500


@app.route("/backends", methods=["GET"])
def get_backends():
    return jsonify(list_all_backends())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
