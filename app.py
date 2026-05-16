"""
QML DataFlow Studio — Single-server entry point.
Flask serves the frontend (frontend/) and all API routes (/api/) from one process.
Start with:  python app.py   or   python start.py
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

FRONTEND_DIR = ROOT_DIR / "frontend"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT_DIR / "uploads")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(ROOT_DIR / "models")))
UPLOAD_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

# ── Flask ──────────────────────────────────────────────────────────────────────
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=CORS_ORIGINS)

# ── Backend imports ────────────────────────────────────────────────────────────
from backend.quantum_runner import list_execution_backends, rebuild_classifier, run_pipeline
from backend.dataset_catalog import DATASET_CONFIGS
from backend.pipeline_registry import ANSATZ_REGISTRY, ENCODER_REGISTRY, OPTIMIZER_REGISTRY


# ═════════════════════════════════════════════════════════════════════════════
# Frontend serving
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file(FRONTEND_DIR / "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    # Don't intercept /api/ routes
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(FRONTEND_DIR, path)


# ═════════════════════════════════════════════════════════════════════════════
# API — Health & Registry
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0.0"})


@app.route("/api/registry", methods=["GET"])
def get_registry():
    """All available encoders, ansatze, optimizers, and domain datasets."""
    datasets_meta = {
        k: {
            "label": v["domain"],
            "description": v["description"],
            "feature_columns": v["feature_columns"],
            "label_column": v["label_column"],
            "recommended": v.get("recommended", {}),
        }
        for k, v in DATASET_CONFIGS.items()
    }
    return jsonify({
        "encoders": ENCODER_REGISTRY,
        "ansatze": ANSATZ_REGISTRY,
        "optimizers": OPTIMIZER_REGISTRY,
        "datasets": datasets_meta,
    })


@app.route("/api/backends", methods=["GET"])
def get_backends():
    return jsonify(list_execution_backends())


# ═════════════════════════════════════════════════════════════════════════════
# API — Datasets
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/dataset/<dataset_name>", methods=["GET"])
def get_dataset(dataset_name):
    import pandas as pd
    try:
        if dataset_name not in DATASET_CONFIGS:
            return jsonify({"error": f"Unknown dataset '{dataset_name}'."}), 400
        cfg = DATASET_CONFIGS[dataset_name]
        p = Path(cfg["path"])
        if not p.exists():
            return jsonify({"error": f"Dataset file missing: {p.name}"}), 404
        df = pd.read_csv(p)
        selected_cols = cfg["feature_columns"] + [cfg["label_column"]]
        return jsonify({
            "ok": True,
            "name": dataset_name,
            "path": str(p.relative_to(ROOT_DIR)).replace("\\", "/"),
            "label_column": cfg["label_column"],
            "feature_columns": cfg["feature_columns"],
            "columns": df.columns.tolist(),
            "n_rows": len(df),
            "description": cfg["description"],
            "domain": cfg["domain"],
            "recommended": cfg.get("recommended", {}),
            "preview": df.head(8).to_dict(orient="records"),
            "stats": _col_stats(df, selected_cols),
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/upload", methods=["POST"])
def upload():
    """Accept CSV or XLSX file, save to uploads/, return column metadata."""
    import pandas as pd
    if "file" not in request.files:
        return jsonify({"error": "No file in request (field name: 'file')"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    safe = secure_filename(f.filename)
    dest = UPLOAD_DIR / safe
    f.save(dest)

    try:
        df = pd.read_excel(dest) if ext in {".xlsx", ".xls"} else pd.read_csv(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        return jsonify({"error": f"Could not parse file: {e}"}), 400

    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    return jsonify({
        "ok": True,
        "path": f"uploads/{safe}",
        "filename": safe,
        "columns": cols,
        "numeric_columns": numeric_cols,
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "n_rows": len(df),
        "preview": df.head(8).to_dict(orient="records"),
        "stats": _col_stats(df, cols[:12]),
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Return missing-value counts and class-balance info for a mapped dataset."""
    import pandas as pd
    try:
        body = request.get_json(force=True) or {}
        raw_path = body.get("path")
        label_col = body.get("label_column")
        feature_cols = body.get("feature_columns") or []
        if not raw_path:
            return jsonify({"error": "path is required"}), 400

        p = Path(raw_path)
        if not p.is_absolute():
            p = ROOT_DIR / raw_path
        if not p.exists():
            return jsonify({"error": f"File not found: {raw_path}"}), 404

        ext = p.suffix.lower()
        df = pd.read_excel(p) if ext in {".xlsx", ".xls"} else pd.read_csv(p)

        check_cols = ([label_col] if label_col and label_col in df.columns else []) + \
                     [c for c in feature_cols if c in df.columns]
        if not check_cols:
            check_cols = df.columns.tolist()

        missing = {c: int(df[c].isna().sum()) for c in check_cols}
        class_balance = None
        if label_col and label_col in df.columns:
            vc = {str(k): int(v) for k, v in df[label_col].value_counts(dropna=True).items()}
            class_balance = {
                "value_counts": vc,
                "n_rows": len(df),
                "n_missing_label": int(df[label_col].isna().sum()),
            }

        return jsonify({
            "ok": True,
            "columns": df.columns.tolist(),
            "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
            "missing_counts": missing,
            "class_balance": class_balance,
            "n_rows": len(df),
            "stats": _col_stats(df, check_cols[:8]),
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ═════════════════════════════════════════════════════════════════════════════
# API — Pipeline execution
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/run", methods=["POST"])
def run():
    req_id = str(uuid.uuid4())[:8]
    t0 = time.time()
    logger.info(f"[{req_id}] /api/run start")
    try:
        spec = request.get_json(force=True)
        if not spec:
            return jsonify({"status": "error", "error": "Empty request body"}), 400
        result = run_pipeline(spec)
        elapsed = round(time.time() - t0, 2)
        result.setdefault("status", "ok")
        result["request_id"] = req_id
        result["execution_time_s"] = elapsed
        logger.info(f"[{req_id}] done in {elapsed}s | acc={result.get('accuracy','?')}")
        return jsonify(result)
    except ValueError as e:
        logger.warning(f"[{req_id}] validation error: {e}")
        return jsonify({"status": "error", "request_id": req_id, "error": str(e)}), 400
    except ImportError as e:
        logger.error(f"[{req_id}] import error: {e}")
        return jsonify({"status": "error", "request_id": req_id, "error": str(e)}), 500
    except Exception as e:
        logger.error(f"[{req_id}] error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error", "request_id": req_id,
            "error": str(e), "trace": traceback.format_exc(),
        }), 500


@app.route("/api/run/batch", methods=["POST"])
def run_batch():
    """Run 2–4 pipeline configurations and return side-by-side results."""
    req_id = str(uuid.uuid4())[:8]
    logger.info(f"[{req_id}] /api/run/batch start")
    try:
        specs = request.get_json(force=True)
        if not isinstance(specs, list):
            return jsonify({"error": "Expected a JSON array of pipeline specs"}), 400
        if not (2 <= len(specs) <= 4):
            return jsonify({"error": "Provide 2–4 pipeline specs for comparison"}), 400
        results = []
        for i, spec in enumerate(specs):
            t0 = time.time()
            try:
                r = run_pipeline(spec)
                r["execution_time_s"] = round(time.time() - t0, 2)
                results.append({"index": i, "status": "ok",
                                 "label": _spec_label(spec), "result": r})
            except Exception as e:
                results.append({"index": i, "status": "error",
                                 "label": _spec_label(spec), "error": str(e)})
        return jsonify({"batch_results": results, "request_id": req_id})
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/predict", methods=["POST"])
def predict():
    """Run predictions on new data using a previously trained model."""
    import joblib
    import pandas as pd

    try:
        body = request.get_json(force=True) or {}
        model_id = body.get("model_id")
        data_path = body.get("path")
        feature_columns = body.get("feature_columns")

        if not model_id:
            return jsonify({"error": "model_id is required"}), 400
        if not data_path:
            return jsonify({"error": "path is required"}), 400

        model_file = MODELS_DIR / f"{model_id}.joblib"
        if not model_file.exists():
            return jsonify({"error": f"Model '{model_id}' not found. Run training first."}), 404

        saved = joblib.load(model_file)
        # Rebuild VQC from saved weights + spec (the VQC object itself is not
        # picklable because it contains a local closure — see quantum_runner.py)
        classifier = rebuild_classifier(saved["weights"], saved["spec"])
        scaler = saved["scaler"]
        cols = feature_columns or saved.get("feature_columns", [])
        if not cols:
            return jsonify({"error": "feature_columns required for prediction"}), 400

        p = Path(data_path)
        if not p.is_absolute():
            p = ROOT_DIR / data_path
        if not p.exists():
            return jsonify({"error": f"Data file not found: {data_path}"}), 404

        ext = p.suffix.lower()
        df = pd.read_excel(p) if ext in {".xlsx", ".xls"} else pd.read_csv(p)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            return jsonify({"error": f"Missing columns in file: {missing}"}), 400

        import numpy as np
        X = df[cols].astype(float).to_numpy()
        X_scaled = scaler.transform(X)

        raw_preds = np.asarray(classifier.predict(X_scaled))
        # VQC may return one-hot arrays ([1,0] or [0,1]) for binary classification.
        # Collapse to a flat integer vector in either case.
        if raw_preds.ndim == 2:
            preds = np.argmax(raw_preds, axis=1).astype(int).tolist()
        else:
            preds = raw_preds.astype(int).tolist()

        proba = None
        try:
            if hasattr(classifier, "predict_proba"):
                p_arr = np.asarray(classifier.predict_proba(X_scaled))
                if p_arr.ndim == 2 and p_arr.shape[1] >= 2:
                    proba = np.round(p_arr[:, 1], 4).tolist()
                elif p_arr.ndim == 1:
                    proba = np.round(p_arr, 4).tolist()
        except Exception:
            pass

        result_rows = df.copy()
        result_rows["prediction"] = preds
        result_rows["risk_label"] = ["HIGH RISK" if p == 1 else "low risk" for p in preds]
        if proba is not None:
            result_rows["probability_class1"] = proba

        return jsonify({
            "ok": True,
            "model_id": model_id,
            "n_samples": len(preds),
            "predictions": preds,
            "probabilities": proba,
            "feature_columns": cols,
            "results_preview": result_rows.head(20).fillna("").to_dict(orient="records"),
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _col_stats(df, columns: list) -> dict:
    import pandas as pd
    stats = {}
    for col in columns:
        if col not in df.columns:
            continue
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            stats[col] = {
                "type": "numeric",
                "mean": round(float(s.mean()), 4) if s.notna().any() else None,
                "std": round(float(s.std()), 4) if s.notna().any() else None,
                "min": round(float(s.min()), 4) if s.notna().any() else None,
                "max": round(float(s.max()), 4) if s.notna().any() else None,
                "null_count": int(s.isna().sum()),
            }
        else:
            vc = s.value_counts(dropna=True).head(5)
            stats[col] = {
                "type": "categorical",
                "unique": int(s.nunique()),
                "top_values": {str(k): int(v) for k, v in vc.items()},
                "null_count": int(s.isna().sum()),
            }
    return stats


def _spec_label(spec: dict) -> str:
    ds = spec.get("dataset", {}).get("name", "dataset")
    enc = spec.get("encoder", {}).get("type", "enc")
    cir = spec.get("circuit", {}).get("type", "cir")
    opt = spec.get("optimizer", {}).get("type", "opt")
    return f"{ds} | {enc} | {cir} | {opt}"


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"QML DataFlow Studio starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
