import json
import os

def load_model(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def save_model(file_path, model):
    with open(file_path, 'w') as f:
        json.dump(model, f)

def model_exists(file_path):
    return os.path.isfile(file_path)