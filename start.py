#!/usr/bin/env python3
"""
QML DataFlow Studio — Local startup script.
Usage: python start.py
"""
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── Python version check ──────────────────────────────────────────────────────
if sys.version_info < (3, 9):
    print(f"ERROR: Python 3.9+ is required. Found {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

# ── Bootstrap .env from example if missing ────────────────────────────────────
env_file = ROOT / ".env"
env_example = ROOT / ".env.example"
if not env_file.exists() and env_example.exists():
    shutil.copy(env_example, env_file)
    print("Created .env from .env.example — edit it to customise settings.")

# ── Ensure required directories exist ────────────────────────────────────────
for d in ["uploads", "models", "logs", "frontend", "datasets"]:
    (ROOT / d).mkdir(exist_ok=True)

# ── Check frontend files present ─────────────────────────────────────────────
missing_frontend = [f for f in ["index.html", "app.js", "style.css"]
                    if not (ROOT / "frontend" / f).exists()]
if missing_frontend:
    print(f"WARNING: Missing frontend files: {missing_frontend}")
    print("         Run from the project root directory.")

# ── Start server ──────────────────────────────────────────────────────────────
import os
port = int(os.getenv("PORT", 5000))
print("=" * 55)
print("  QML DataFlow Studio")
print(f"  Open http://localhost:{port} in your browser")
print("  Press Ctrl+C to stop")
print("=" * 55)

subprocess.run([sys.executable, str(ROOT / "app.py")], cwd=str(ROOT))
