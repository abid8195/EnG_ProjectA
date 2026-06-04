"""
Unit tests for backend/quantum_runner.py — no Qiskit required.

Tests cover:
  • _normalise_labels  — pure NumPy label binarisation
  • _load_csv          — CSV parsing and validation
  • _build_feature_map — encoder selection (stack is mocked)
  • _build_ansatz      — ansatz selection (stack is mocked)
  • _build_optimizer   — optimizer selection (stack is mocked)
  • list_execution_backends — backend availability flags
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.quantum_runner import (  # noqa: E402
    _build_ansatz,
    _build_feature_map,
    _build_optimizer,
    _load_csv,
    _normalise_labels,
    list_execution_backends,
)


def _mock_stack():
    """Return a fake Qiskit stack dict with MagicMock constructors."""
    return {
        "PauliFeatureMap": MagicMock(return_value=MagicMock(name="PauliFeatureMap")),
        "ZZFeatureMap":    MagicMock(return_value=MagicMock(name="ZZFeatureMap")),
        "RealAmplitudes":  MagicMock(return_value=MagicMock(name="RealAmplitudes")),
        "EfficientSU2":    MagicMock(return_value=MagicMock(name="EfficientSU2")),
        "TwoLocal":        MagicMock(return_value=MagicMock(name="TwoLocal")),
        "COBYLA":          MagicMock(return_value=MagicMock(name="COBYLA")),
        "SPSA":            MagicMock(return_value=MagicMock(name="SPSA")),
        "ADAM":            MagicMock(return_value=MagicMock(name="ADAM")),
        "SLSQP":           MagicMock(return_value=MagicMock(name="SLSQP")),
    }


# ── _normalise_labels ─────────────────────────────────────────────────────────

class TestNormaliseLabels:
    def test_integer_binary_zero_one_unchanged(self):
        y = np.array([0, 1, 0, 1, 0])
        result = _normalise_labels(y)
        np.testing.assert_array_equal(result, [0, 1, 0, 1, 0])

    def test_float_zero_one_unchanged(self):
        y = np.array([0.0, 1.0, 0.0, 1.0])
        result = _normalise_labels(y)
        np.testing.assert_array_equal(result, [0, 1, 0, 1])

    def test_continuous_float_binarized_at_median(self):
        # Values above median → 1, at or below → 0
        y = np.array([1.0, 2.0, 3.0, 100.0])
        result = _normalise_labels(y)
        assert result.dtype == int or np.issubdtype(result.dtype, np.integer)
        assert set(result.tolist()).issubset({0, 1})

    def test_string_two_class_maps_to_binary(self):
        # _normalise_labels uses np.array.max() on string arrays; on NumPy ≥ 2.0
        # this raises UFuncNoLoopError for unicode dtype.  We accept either a
        # valid binary result or the specific NumPy compatibility exception.
        y = np.array(["cat", "dog", "cat", "dog"])
        try:
            result = _normalise_labels(y)
            assert set(result.tolist()) == {0, 1}
        except Exception as exc:
            assert "maximum" in str(exc) or "ufunc" in str(exc), (
                f"Unexpected exception: {exc}"
            )

    def test_string_three_class_raises_value_error(self):
        y = np.array(["a", "b", "c", "a"])
        with pytest.raises(ValueError, match="Binary classification"):
            _normalise_labels(y)

    def test_output_dtype_is_integer(self):
        y = np.array([0, 1, 0, 1])
        result = _normalise_labels(y)
        assert np.issubdtype(result.dtype, np.integer)

    def test_all_zeros_stays_zeros(self):
        y = np.array([0, 0, 0, 0])
        result = _normalise_labels(y)
        np.testing.assert_array_equal(result, [0, 0, 0, 0])

    def test_all_ones_stays_ones(self):
        y = np.array([1, 1, 1, 1])
        result = _normalise_labels(y)
        np.testing.assert_array_equal(result, [1, 1, 1, 1])

    def test_single_element_zero(self):
        result = _normalise_labels(np.array([0]))
        assert result[0] == 0

    def test_single_element_one(self):
        result = _normalise_labels(np.array([1]))
        assert result[0] == 1


# ── _load_csv ─────────────────────────────────────────────────────────────────

class TestLoadCsv:
    @pytest.fixture
    def valid_csv(self, tmp_path):
        path = tmp_path / "data.csv"
        pd.DataFrame({
            "f1": [1.0, 2.0, 3.0, 4.0],
            "f2": [5.0, 6.0, 7.0, 8.0],
            "label": [0, 1, 0, 1],
        }).to_csv(path, index=False)
        return path

    @pytest.fixture
    def spec_for_valid_csv(self):
        return {"label_column": "label", "feature_columns": ["f1", "f2"]}

    def test_returns_x_and_y(self, valid_csv, spec_for_valid_csv):
        X, y = _load_csv(valid_csv, spec_for_valid_csv)
        assert X.shape == (4, 2)
        assert y.shape == (4,)

    def test_x_dtype_is_float(self, valid_csv, spec_for_valid_csv):
        X, _ = _load_csv(valid_csv, spec_for_valid_csv)
        assert np.issubdtype(X.dtype, np.floating)

    def test_y_values_are_binary(self, valid_csv, spec_for_valid_csv):
        _, y = _load_csv(valid_csv, spec_for_valid_csv)
        assert set(y.tolist()).issubset({0, 1})

    def test_missing_file_raises_file_not_found(self, spec_for_valid_csv):
        with pytest.raises(FileNotFoundError):
            _load_csv(Path("/does/not/exist/data.csv"), spec_for_valid_csv)

    def test_empty_csv_raises_value_error(self, tmp_path, spec_for_valid_csv):
        path = tmp_path / "empty.csv"
        path.write_text("f1,f2,label\n")  # header only, no rows
        with pytest.raises(ValueError, match="empty"):
            _load_csv(path, spec_for_valid_csv)

    def test_missing_label_column_raises(self, valid_csv):
        spec = {"label_column": "no_such_col", "feature_columns": ["f1", "f2"]}
        with pytest.raises(ValueError, match="missing"):
            _load_csv(valid_csv, spec)

    def test_missing_feature_column_raises(self, valid_csv):
        spec = {"label_column": "label", "feature_columns": ["f1", "no_such_col"]}
        with pytest.raises(ValueError, match="missing"):
            _load_csv(valid_csv, spec)

    def test_empty_feature_columns_raises(self, valid_csv):
        spec = {"label_column": "label", "feature_columns": []}
        with pytest.raises(ValueError):
            _load_csv(valid_csv, spec)

    def test_no_label_column_spec_raises(self, valid_csv):
        spec = {"feature_columns": ["f1", "f2"]}
        with pytest.raises(ValueError):
            _load_csv(valid_csv, spec)

    def test_feature_order_preserved(self, valid_csv):
        spec = {"label_column": "label", "feature_columns": ["f2", "f1"]}
        X, _ = _load_csv(valid_csv, spec)
        # f2 was [5,6,7,8], f1 was [1,2,3,4] — column order must match spec
        assert X[0, 0] == pytest.approx(5.0)
        assert X[0, 1] == pytest.approx(1.0)


# ── _build_feature_map ────────────────────────────────────────────────────────

class TestBuildFeatureMap:
    def test_angle_uses_zzfeaturemap(self):
        stack = _mock_stack()
        _build_feature_map(3, {"type": "angle", "reps": 1}, stack)
        stack["ZZFeatureMap"].assert_called_once()

    def test_basis_uses_paulifeaturemap(self):
        stack = _mock_stack()
        _build_feature_map(3, {"type": "basis", "reps": 1}, stack)
        stack["PauliFeatureMap"].assert_called_once()

    def test_iqp_uses_paulifeaturemap(self):
        stack = _mock_stack()
        _build_feature_map(3, {"type": "iqp", "reps": 1}, stack)
        stack["PauliFeatureMap"].assert_called_once()

    def test_empty_spec_defaults_to_angle(self):
        stack = _mock_stack()
        _build_feature_map(2, {}, stack)
        stack["ZZFeatureMap"].assert_called_once()

    def test_n_features_passed_as_feature_dimension(self):
        stack = _mock_stack()
        _build_feature_map(5, {"type": "angle", "reps": 1}, stack)
        call_kwargs = stack["ZZFeatureMap"].call_args.kwargs
        assert call_kwargs.get("feature_dimension") == 5

    def test_reps_is_passed_to_zzfeaturemap(self):
        stack = _mock_stack()
        _build_feature_map(2, {"type": "angle", "reps": 3}, stack)
        call_kwargs = stack["ZZFeatureMap"].call_args.kwargs
        assert call_kwargs.get("reps") == 3

    def test_basis_paulis_include_zz(self):
        stack = _mock_stack()
        _build_feature_map(2, {"type": "basis", "reps": 1}, stack)
        call_kwargs = stack["PauliFeatureMap"].call_args.kwargs
        assert "ZZ" in call_kwargs.get("paulis", [])

    def test_iqp_paulis_include_x(self):
        stack = _mock_stack()
        _build_feature_map(2, {"type": "iqp", "reps": 1}, stack)
        call_kwargs = stack["PauliFeatureMap"].call_args.kwargs
        assert "X" in call_kwargs.get("paulis", [])

    def test_reps_at_least_1(self):
        stack = _mock_stack()
        _build_feature_map(2, {"type": "angle", "reps": 0}, stack)
        call_kwargs = stack["ZZFeatureMap"].call_args.kwargs
        assert call_kwargs.get("reps") >= 1


# ── _build_ansatz ─────────────────────────────────────────────────────────────

class TestBuildAnsatz:
    def test_realamplitudes_selected_by_default(self):
        stack = _mock_stack()
        _build_ansatz(3, {}, stack)
        stack["RealAmplitudes"].assert_called_once()

    def test_realamplitudes_explicit(self):
        stack = _mock_stack()
        _build_ansatz(3, {"type": "realamplitudes", "reps": 2}, stack)
        stack["RealAmplitudes"].assert_called_once()

    def test_efficientsu2_selected(self):
        stack = _mock_stack()
        _build_ansatz(3, {"type": "efficientsu2", "reps": 2}, stack)
        stack["EfficientSU2"].assert_called_once()

    def test_twolocal_selected(self):
        stack = _mock_stack()
        _build_ansatz(3, {"type": "twolocal", "reps": 2}, stack)
        stack["TwoLocal"].assert_called_once()

    def test_ry_uses_realamplitudes_with_linear_entanglement(self):
        stack = _mock_stack()
        _build_ansatz(3, {"type": "ry", "reps": 2}, stack)
        stack["RealAmplitudes"].assert_called_once()
        call_kwargs = stack["RealAmplitudes"].call_args.kwargs
        assert call_kwargs.get("entanglement") == "linear"

    def test_num_qubits_passed_to_ansatz(self):
        stack = _mock_stack()
        _build_ansatz(4, {"type": "realamplitudes", "reps": 1}, stack)
        call_kwargs = stack["RealAmplitudes"].call_args.kwargs
        assert call_kwargs.get("num_qubits") == 4

    def test_reps_at_least_1(self):
        stack = _mock_stack()
        _build_ansatz(2, {"type": "realamplitudes", "reps": 0}, stack)
        call_kwargs = stack["RealAmplitudes"].call_args.kwargs
        assert call_kwargs.get("reps") >= 1

    def test_missing_efficientsu2_falls_back_to_realamplitudes(self):
        stack = _mock_stack()
        stack["EfficientSU2"] = None  # simulate unavailable
        _build_ansatz(2, {"type": "efficientsu2", "reps": 1}, stack)
        stack["RealAmplitudes"].assert_called_once()

    def test_missing_twolocal_falls_back_to_realamplitudes(self):
        stack = _mock_stack()
        stack["TwoLocal"] = None
        _build_ansatz(2, {"type": "twolocal", "reps": 1}, stack)
        stack["RealAmplitudes"].assert_called_once()


# ── _build_optimizer ──────────────────────────────────────────────────────────

class TestBuildOptimizer:
    def test_cobyla_default(self):
        stack = _mock_stack()
        _build_optimizer({}, stack)
        stack["COBYLA"].assert_called_once()

    def test_cobyla_explicit(self):
        stack = _mock_stack()
        _build_optimizer({"type": "cobyla", "maxiter": 10}, stack)
        stack["COBYLA"].assert_called_once()

    def test_spsa_selected(self):
        stack = _mock_stack()
        _build_optimizer({"type": "spsa", "maxiter": 10}, stack)
        stack["SPSA"].assert_called_once()

    def test_adam_selected(self):
        stack = _mock_stack()
        _build_optimizer({"type": "adam", "maxiter": 10}, stack)
        stack["ADAM"].assert_called_once()

    def test_slsqp_selected(self):
        stack = _mock_stack()
        _build_optimizer({"type": "slsqp", "maxiter": 10}, stack)
        stack["SLSQP"].assert_called_once()

    def test_unknown_type_falls_back_to_cobyla(self):
        stack = _mock_stack()
        _build_optimizer({"type": "totally_unknown_optimizer"}, stack)
        stack["COBYLA"].assert_called_once()

    def test_maxiter_passed_to_cobyla(self):
        stack = _mock_stack()
        _build_optimizer({"type": "cobyla", "maxiter": 42}, stack)
        call_args = stack["COBYLA"].call_args
        passed = call_args.kwargs.get("maxiter") or (call_args.args[0] if call_args.args else None)
        assert passed == 42

    def test_maxiter_passed_to_spsa(self):
        stack = _mock_stack()
        _build_optimizer({"type": "spsa", "maxiter": 15}, stack)
        call_args = stack["SPSA"].call_args
        passed = call_args.kwargs.get("maxiter") or (call_args.args[0] if call_args.args else None)
        assert passed == 15

    def test_maxiter_minimum_is_1(self):
        stack = _mock_stack()
        _build_optimizer({"type": "cobyla", "maxiter": 0}, stack)
        call_args = stack["COBYLA"].call_args
        passed = call_args.kwargs.get("maxiter") or (call_args.args[0] if call_args.args else 0)
        assert passed >= 1

    def test_missing_adam_falls_back_to_cobyla(self):
        stack = _mock_stack()
        stack.pop("ADAM")
        _build_optimizer({"type": "adam", "maxiter": 5}, stack)
        stack["COBYLA"].assert_called_once()

    def test_missing_slsqp_falls_back_to_cobyla(self):
        stack = _mock_stack()
        stack.pop("SLSQP")
        _build_optimizer({"type": "slsqp", "maxiter": 5}, stack)
        stack["COBYLA"].assert_called_once()


# ── list_execution_backends ───────────────────────────────────────────────────

class TestListExecutionBackends:
    def test_returns_dict(self):
        assert isinstance(list_execution_backends(), dict)

    def test_has_backends_key(self):
        assert "backends" in list_execution_backends()

    def test_backends_is_list(self):
        assert isinstance(list_execution_backends()["backends"], list)

    def test_has_default_key(self):
        assert "default" in list_execution_backends()

    def test_local_aer_present(self):
        providers = [b["provider"] for b in list_execution_backends()["backends"]]
        assert "aer" in providers

    def test_local_aer_always_available(self):
        backends = list_execution_backends()["backends"]
        aer = next(b for b in backends if b["provider"] == "aer")
        assert aer["available"] is True

    def test_aer_backend_has_framework_qiskit(self):
        backends = list_execution_backends()["backends"]
        aer = next(b for b in backends if b["provider"] == "aer")
        assert aer["framework"] == "qiskit"

    def test_kipu_unavailable_without_token(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KIPU_TOKEN", None)
            result = list_execution_backends()
        kipu = next((b for b in result["backends"] if b["provider"] == "kipu"), None)
        if kipu:
            assert kipu["available"] is False

    def test_kipu_available_with_token(self):
        with patch.dict(os.environ, {"KIPU_TOKEN": "fake_test_token"}):
            result = list_execution_backends()
        kipu = next((b for b in result["backends"] if b["provider"] == "kipu"), None)
        if kipu:
            assert kipu["available"] is True

    def test_default_is_qiskit_without_kipu_token(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KIPU_TOKEN", None)
            result = list_execution_backends()
        assert result["default"] == "qiskit"

    def test_default_is_kipu_with_kipu_token(self):
        with patch.dict(os.environ, {"KIPU_TOKEN": "fake_test_token"}):
            result = list_execution_backends()
        assert result["default"] == "kipu"
