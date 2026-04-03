# backend/app.py  — Sprint 2
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
    kipu_available = bool(os.getenv("KIPU_ACCESS_TOKEN", "").strip())
    try:
        import qiskit_aer
        aer_available = True
    except ImportError:
        aer_available = False

    return jsonify({
        "status": "ok",
        "kipu_token_set": kipu_available,
        "aer_available": aer_available,
        "quantum_ready": kipu_available or aer_available,
    })


@app.route("/backends", methods=["GET"])
def backends():
    """
    Returns which quantum backends are currently available.
    The frontend uses this to enable/disable the Kipu mode selector.
    """
    kipu_token = bool(os.getenv("KIPU_ACCESS_TOKEN", "").strip())
    try:
        import qiskit_aer
        aer_ok = True
    except ImportError:
        aer_ok = False

    available = []
    if kipu_token:
        available.append({
            "id": "kipu_simulator",
            "label": "Kipu Quantum Hub",
            "ready": True,
        })
    available.append({
        "id": "aer_simulator",
        "label": "Local AerSimulator (fallback)",
        "ready": aer_ok,
    })
    available.append({
        "id": "classical",
        "label": "Classical (LogisticRegression)",
        "ready": True,
    })

    return jsonify({"backends": available})


@app.route("/upload", methods=["POST"])
def upload():
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "error": "No file part"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"status": "error", "error": "Please upload a .csv file"}), 400

    dest = os.path.join(UPLOAD_DIR, f.filename)
    f.save(dest)

    try:
        df = pd.read_csv(dest)
    except Exception as e:
        return jsonify({"status": "error", "error": f"Failed to read CSV: {e}"}), 400

    return jsonify({
        "ok": True,
        "path": f"uploads/{f.filename}",
        "columns": df.columns.tolist(),
        "preview": df.head(5).to_dict(orient="records")
    })


@app.route("/run", methods=["POST"])
def run():
    """
    Execute the QML pipeline (quantum or classical based on execution_mode).
    Sprint 2: consistent status field; handles all new dataset types.
    """
    try:
        spec = request.get_json(force=True)
        out = run_pipeline(spec)

        if isinstance(out, dict) and "status" not in out:
            out["status"] = "ok"
        return jsonify(out)

    except ValueError as e:
        return jsonify({"status": "error", "error": str(e)}), 400

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


DATASET_REGISTRY = {
    "diabetes": {
        "path": "datasets/diabetes.csv",
        "label_column": "outcome",
        "feature_columns": ["pregnancies", "glucose", "bloodpressure", "bmi", "age"],
        "description": "Diabetes prediction dataset",
        "runner_type": "csv",
        "category": "healthcare",
    },
    "iris": {
        "path": "datasets/iris.csv",
        "label_column": "species",
        "feature_columns": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
        "description": "Iris flower classification dataset",
        "runner_type": "iris",
        "category": "classic",
    },
    "realestate": {
        "path": "datasets/realestate.csv",
        "label_column": "price_high",
        "feature_columns": ["size", "bedrooms", "bathrooms", "age", "location_score"],
        "description": "Real estate price prediction dataset",
        "runner_type": "csv",
        "category": "business",
    },
    "finance": {
        "path": "datasets/finance.csv",
        "label_column": "beats_market",
        "feature_columns": ["pe_ratio", "debt_equity", "revenue_growth",
                            "market_cap_log", "volatility"],
        "description": "Stock market outperformance prediction (Finance)",
        "runner_type": "csv",
        "category": "finance",
    },
    "hr": {
        "path": "datasets/hr_attrition.csv",
        "label_column": "stayed",
        "feature_columns": ["satisfaction_level", "last_evaluation",
                            "number_projects", "average_monthly_hours",
                            "years_at_company"],
        "description": "Employee attrition / retention prediction (HR)",
        "runner_type": "csv",
        "category": "hr",
    },
    "supply_chain": {
        "path": "datasets/supply_chain.csv",
        "label_column": "on_time",
        "feature_columns": ["distance_km", "weight_kg", "weather_score",
                            "carrier_rating", "warehouse_fill_ratio"],
        "description": "Delivery on-time prediction (Supply Chain)",
        "runner_type": "csv",
        "category": "logistics",
    },
    "wine_industry": {
        "path": "datasets/wine_industry.csv",
        "label_column": "quality_high",
        "feature_columns": ["acidity", "residual_sugar", "alcohol", "sulphates", "pH"],
        "description": "Wine quality prediction (Wine Industry)",
        "runner_type": "csv",
        "category": "industry",
    },
    "cake_industry": {
        "path": "datasets/cake_industry.csv",
        "label_column": "sales_high",
        "feature_columns": ["avg_order_value", "custom_orders_weekly",
                            "production_time_hours", "seasonal_demand_index",
                            "rating_score"],
        "description": "Cake sales performance prediction (Cake Industry)",
        "runner_type": "csv",
        "category": "industry",
    },
    "computer_processor": {
        "path": "datasets/computer_processor_industry.csv",
        "label_column": "performance_high",
        "feature_columns": ["cores", "threads", "base_clock_ghz",
                            "boost_clock_ghz", "l3_cache_mb", "tdp_w"],
        "description": "Processor performance prediction (Computer Industry)",
        "runner_type": "csv",
        "category": "industry",
    },
}


@app.route("/datasets", methods=["GET"])
def list_datasets():
    """NEW Sprint 2 endpoint: returns the full dataset registry as a list."""
    result = []
    for name, cfg in DATASET_REGISTRY.items():
        result.append({
            "name": name,
            "label_column": cfg["label_column"],
            "feature_columns": cfg["feature_columns"],
            "description": cfg["description"],
            "category": cfg.get("category", "other"),
        })
    return jsonify({"datasets": result})


@app.route("/dataset/<dataset_name>", methods=["GET"])
def get_dataset(dataset_name):
    """Return config + preview for a named dataset."""
    try:
        if dataset_name not in DATASET_REGISTRY:
            available = list(DATASET_REGISTRY.keys())
            return jsonify({
                "status": "error",
                "error": f"Unknown dataset: '{dataset_name}'",
                "available": available,
            }), 400

        cfg = DATASET_REGISTRY[dataset_name]
        dataset_path = os.path.join(os.path.dirname(__file__), cfg["path"])

        if not os.path.exists(dataset_path):
            return jsonify({
                "status": "error",
                "error": f"Dataset file not found: {cfg['path']}"
            }), 404

        df = pd.read_csv(dataset_path)

        return jsonify({
            "ok": True,
            "name": dataset_name,
            "path": cfg["path"],
            "runner_type": cfg.get("runner_type", "csv"),
            "label_column": cfg["label_column"],
            "feature_columns": cfg["feature_columns"],
            "columns": df.columns.tolist(),
            "description": cfg["description"],
            "category": cfg.get("category", "other"),
            "row_count": len(df),
            "preview": df.head(5).to_dict(orient="records"),
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Failed to load dataset: {e}",
            "trace": traceback.format_exc()
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
