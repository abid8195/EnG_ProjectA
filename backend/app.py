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
        if isinstance(out, dict) and out.get("error"):
            return jsonify({"status": "error", "error": out.get("error"), "received_spec": out.get("received_spec", spec)}), 400
        return jsonify({"status": "ok", "result": out})
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

@app.route("/instructions", methods=["GET"])
def instructions():
    """
    Return a downloadable plain-text instruction file for using the CSV QML pipeline.
    """
    from flask import make_response
    lines = []
    lines.append("QML Pipeline Instructions\n")
    lines.append("==========================\n\n")
    lines.append("Required dataset format:\n")
    lines.append("- CSV with a header row.\n")
    lines.append("- Numeric feature columns (non-numeric will be rejected or imputed as NaN).\n")
    lines.append("- One label column (string or numeric). Multiclass is temporarily reduced to two most frequent classes.\n\n")
    lines.append("How to use the UI (step-by-step):\n")
    lines.append("1) Upload your CSV via the Upload panel. The server saves it under backend/uploads.\n")
    lines.append("2) Choose label_column and feature_columns from the detected headers.\n")
    lines.append("3) Select num_qubits (the model will apply PCA to match this dimension).\n")
    lines.append("4) Pick reps for the RealAmplitudes ansatz and COBYLA max iterations.\n")
    lines.append("5) Click Run. The backend will train an EstimatorQNN and return accuracy and a small predictions preview.\n\n")
    lines.append("Preprocessing notes:\n")
    lines.append("- Missing values are imputed with median (per feature).\n")
    lines.append("- Features are standardized with StandardScaler.\n")
    lines.append("- PCA reduces/aligns feature dimension to num_qubits. If features < num_qubits, the model pads with zeros.\n")
    lines.append("- Multiclass datasets are simplified to a one-vs-one on the two most frequent classes.\n")
    lines.append("- Deterministic seed: algorithm_globals.random_seed = 42.\n\n")
    lines.append("Sample datasets and columns:\n")
    lines.append("- diabetes_small.csv: label 'Outcome'; example features ['Pregnancies','Glucose','BloodPressure','SkinThickness','Insulin','BMI','DiabetesPedigreeFunction','Age']\n")
    lines.append("- iris_like.csv: label 'species'; example features ['sepal_length','sepal_width','petal_length','petal_width']\n")
    lines.append("- wine_small.csv: label 'quality_label'; example features ['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']\n\n")
    lines.append("Outputs:\n")
    lines.append("- On success: {\"message\": \"Training complete\", \"accuracy\": <float>, \"predictions_preview\": {y_true, y_pred}, shapes, num_qubits, reps}.\n")
    lines.append("- On error: HTTP 400 with {\"error\": <message>, \"received_spec\": {...}}.\n")

    content = "".join(lines)
    resp = make_response(content)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=instructions.txt"
    return resp

if __name__ == "__main__":
    # Bind to all interfaces so your frontend at http://localhost:8000 can reach it.
    app.run(host="0.0.0.0", port=5000, debug=True)
