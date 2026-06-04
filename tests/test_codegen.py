"""
Unit tests for backend/codegen.py

Verifies that write_generated_run produces syntactically valid Python code
for both Qiskit (default) and PennyLane frameworks, and that user-provided
spec values are reflected in the generated output.
"""
import ast
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.codegen import write_generated_run  # noqa: E402


def _qiskit_spec(**overrides):
    base = {
        "framework": "qiskit",
        "dataset": {
            "path": "/data/mydata.csv",
            "feature_columns": ["feat1", "feat2"],
            "label_column": "target",
            "test_size": 0.25,
            "seed": 42,
        },
        "circuit": {"num_qubits": 2, "reps": 2},
        "optimizer": {"type": "cobyla", "maxiter": 20},
        "execution": {"shots": 128},
    }
    base.update(overrides)
    return base


def _pennylane_spec(**overrides):
    spec = _qiskit_spec(**overrides)
    spec["framework"] = "pennylane"
    return spec


def _read_generated(spec, tmp_path, name="generated.py"):
    out = str(tmp_path / name)
    write_generated_run(spec, out_path=out)
    return Path(out).read_text(encoding="utf-8"), out


class TestCodegenQiskit:
    def test_creates_file(self, tmp_path):
        out = str(tmp_path / "gen.py")
        write_generated_run(_qiskit_spec(), out_path=out)
        assert Path(out).exists()

    def test_returns_path_string(self, tmp_path):
        out = str(tmp_path / "gen.py")
        result = write_generated_run(_qiskit_spec(), out_path=out)
        assert isinstance(result, str)
        assert result == out

    def test_generated_code_is_valid_python(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated Qiskit code has syntax error: {e}")

    def test_imports_vqc(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "VQC" in code

    def test_imports_sklearn_accuracy(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "accuracy_score" in code

    def test_contains_dataset_path(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "/data/mydata.csv" in code

    def test_contains_feature_columns(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "feat1" in code
        assert "feat2" in code

    def test_contains_label_column(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "target" in code

    def test_contains_optimizer_name_cobyla(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "COBYLA" in code

    def test_contains_spsa_when_specified(self, tmp_path):
        spec = _qiskit_spec()
        spec["optimizer"] = {"type": "spsa", "maxiter": 30}
        code, _ = _read_generated(spec, tmp_path)
        assert "SPSA" in code

    def test_contains_shots_value(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "128" in code

    def test_contains_test_size(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "0.25" in code

    def test_contains_seed(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "42" in code

    def test_contains_aer_simulator(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "AerSimulator" in code

    def test_contains_standard_scaler(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "StandardScaler" in code

    def test_zzfeaturemap_used_by_default(self, tmp_path):
        code, _ = _read_generated(_qiskit_spec(), tmp_path)
        assert "ZZFeatureMap" in code

    def test_paulifeaturemap_used_for_basis_dataset_type(self, tmp_path):
        spec = _qiskit_spec()
        spec["dataset"]["type"] = "basis"
        code, _ = _read_generated(spec, tmp_path)
        assert "PauliFeatureMap" in code

    def test_maxiter_reflected_in_output(self, tmp_path):
        spec = _qiskit_spec()
        spec["optimizer"]["maxiter"] = 99
        code, _ = _read_generated(spec, tmp_path)
        assert "99" in code

    def test_num_qubits_reflected_in_output(self, tmp_path):
        spec = _qiskit_spec()
        spec["circuit"]["num_qubits"] = 7
        code, _ = _read_generated(spec, tmp_path)
        assert "7" in code


class TestCodegenPennyLane:
    def test_creates_file(self, tmp_path):
        out = str(tmp_path / "gen_pl.py")
        write_generated_run(_pennylane_spec(), out_path=out)
        assert Path(out).exists()

    def test_generated_code_is_valid_python(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated PennyLane code has syntax error: {e}")

    def test_imports_pennylane(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "pennylane" in code

    def test_qnode_decorator_present(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "qnode" in code

    def test_contains_dataset_path(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "/data/mydata.csv" in code

    def test_contains_feature_columns(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "feat1" in code

    def test_contains_label_column(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "target" in code

    def test_uses_angle_embedding(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "AngleEmbedding" in code

    def test_uses_strongly_entangling_layers(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "StronglyEntanglingLayers" in code

    def test_contains_shots_value(self, tmp_path):
        code, _ = _read_generated(_pennylane_spec(), tmp_path, "gen_pl.py")
        assert "128" in code


class TestCodegenOutputPath:
    def test_default_path_not_none(self, tmp_path, monkeypatch):
        # Patch ROOT to write into tmp_path so we don't pollute the project
        monkeypatch.chdir(tmp_path)
        import backend.codegen as cg
        original = cg.write_generated_run
        out = write_generated_run(_qiskit_spec())
        assert out is not None
        assert isinstance(out, str)

    def test_custom_path_used(self, tmp_path):
        custom = str(tmp_path / "custom_output.py")
        result = write_generated_run(_qiskit_spec(), out_path=custom)
        assert result == custom
        assert Path(custom).exists()

    def test_custom_directory_respected(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        out = str(subdir / "gen.py")
        write_generated_run(_qiskit_spec(), out_path=out)
        assert (subdir / "gen.py").exists()
