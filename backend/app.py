# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

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

if __name__ == "__main__":
    # Bind to all interfaces so your frontend at http://localhost:8000 can reach it.
    app.run(host="0.0.0.0", port=5000, debug=True)
