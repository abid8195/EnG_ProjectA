"""
Shared fixtures for the QML DataFlow Studio test suite.

All Flask API tests use the `client` fixture; quantum runner unit
tests and catalog tests import backend modules directly.
"""
import io
import sys
from pathlib import Path

import pytest

# Make sure the project root is importable regardless of where pytest runs
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app as flask_app  # noqa: E402  (must follow sys.path insertion)


@pytest.fixture(scope="session")
def client():
    """Session-scoped Flask test client — avoids repeated app teardown."""
    flask_app.config["TESTING"] = True
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def minimal_csv_bytes():
    """Four-row CSV with two features and a binary label column."""
    return b"feature1,feature2,label\n1.0,2.0,0\n3.0,4.0,1\n5.0,6.0,0\n7.0,8.0,1\n"


@pytest.fixture
def large_csv_bytes():
    """Twenty-row CSV for richer statistics checks."""
    header = b"feature1,feature2,feature3,label\n"
    rows = b"".join(
        f"{i * 0.5},{i * 1.1},{i * 0.3},{i % 2}\n".encode()
        for i in range(1, 21)
    )
    return header + rows


@pytest.fixture
def finance_pipeline_spec():
    """Minimal valid async pipeline spec targeting the built-in finance dataset."""
    return {
        "framework": "qiskit",
        "dataset": {
            "name": "finance",
            "test_size": 0.3,
            "seed": 42,
        },
        "encoder": {"type": "angle", "reps": 1},
        "circuit": {"type": "realamplitudes", "num_qubits": 5, "reps": 1},
        "optimizer": {"type": "cobyla", "maxiter": 1},
        "execution": {"provider": "local", "backend": "aer_simulator", "shots": 64},
    }
