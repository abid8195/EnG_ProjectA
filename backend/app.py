from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        return jsonify({
            'ok': True,
            'path': filepath,
            'columns': ['feature1', 'feature2', 'label'],  # Example
            'rows': 100  # Example
        })
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/run', methods=['POST'])
def run_pipeline():
    spec = request.json
    # Mockup response for now
    return jsonify({
        'status': 'success',
        'accuracy': 0.85,
        'n_samples': 100
    })

if __name__ == '__main__':
    app.run(debug=True)