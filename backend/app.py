from flask import Flask, request, jsonify
from flask_cors import CORS
from runner import run_pipeline
from codegen import write_generated_run
import traceback

app = Flask(__name__)
CORS(app)  # allow calls from http://localhost:8080

@app.get("/health")
def health():
    return jsonify({"ok": True}), 200

@app.post("/run")
def run():
    try:
        spec = request.get_json(force=True) or {}
        # minimal required keys check (keeps Sprint-1 simple)
        for key in ("dataset", "circuit", "qnn", "optimizer"):
            if key not in spec:
                return jsonify({"error": f"Missing '{key}' in spec"}), 400

        metrics = run_pipeline(spec)
        code_path = write_generated_run(spec)
        return jsonify({**metrics, "generated_code_path": code_path}), 200
    except Exception as e:
        # short readable error + last line of traceback
        tb = traceback.format_exc().strip().splitlines()[-1]
        return jsonify({"error": f"{e.__class__.__name__}: {str(e)}", "detail": tb}), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)
