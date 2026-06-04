"""
Unit tests for backend/pipeline_registry.py

Verifies that all encoder, ansatz, and optimizer entries exist with the
correct structure so the frontend can build dropdowns without crashing.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.pipeline_registry import (  # noqa: E402
    ANSATZ_REGISTRY,
    ENCODER_REGISTRY,
    OPTIMIZER_REGISTRY,
)

REQUIRED_ENTRY_KEYS = {"label", "description", "qiskit_class"}


class TestEncoderRegistry:
    def test_registry_is_dict(self):
        assert isinstance(ENCODER_REGISTRY, dict)

    def test_registry_not_empty(self):
        assert len(ENCODER_REGISTRY) > 0

    def test_angle_encoder_present(self):
        assert "angle" in ENCODER_REGISTRY

    def test_basis_encoder_present(self):
        assert "basis" in ENCODER_REGISTRY

    def test_iqp_encoder_present(self):
        assert "iqp" in ENCODER_REGISTRY

    def test_angle_has_required_keys(self):
        missing = REQUIRED_ENTRY_KEYS - set(ENCODER_REGISTRY["angle"].keys())
        assert not missing, f"'angle' encoder missing keys: {missing}"

    def test_basis_has_required_keys(self):
        missing = REQUIRED_ENTRY_KEYS - set(ENCODER_REGISTRY["basis"].keys())
        assert not missing, f"'basis' encoder missing keys: {missing}"

    def test_iqp_has_required_keys(self):
        missing = REQUIRED_ENTRY_KEYS - set(ENCODER_REGISTRY["iqp"].keys())
        assert not missing, f"'iqp' encoder missing keys: {missing}"

    def test_angle_qiskit_class_is_zzfeaturemap(self):
        assert ENCODER_REGISTRY["angle"]["qiskit_class"] == "ZZFeatureMap"

    def test_basis_qiskit_class_is_paulifeaturemap(self):
        assert ENCODER_REGISTRY["basis"]["qiskit_class"] == "PauliFeatureMap"

    def test_iqp_qiskit_class_is_paulifeaturemap(self):
        assert ENCODER_REGISTRY["iqp"]["qiskit_class"] == "PauliFeatureMap"

    def test_all_labels_are_non_empty_strings(self):
        for name, entry in ENCODER_REGISTRY.items():
            assert isinstance(entry["label"], str) and entry["label"].strip() != "", \
                f"Encoder '{name}' has empty label"

    def test_all_descriptions_are_non_empty_strings(self):
        for name, entry in ENCODER_REGISTRY.items():
            assert isinstance(entry["description"], str) and entry["description"].strip() != "", \
                f"Encoder '{name}' has empty description"


class TestAnsatzRegistry:
    def test_registry_is_dict(self):
        assert isinstance(ANSATZ_REGISTRY, dict)

    def test_registry_not_empty(self):
        assert len(ANSATZ_REGISTRY) > 0

    def test_realamplitudes_present(self):
        assert "realamplitudes" in ANSATZ_REGISTRY

    def test_efficientsu2_present(self):
        assert "efficientsu2" in ANSATZ_REGISTRY

    def test_twolocal_present(self):
        assert "twolocal" in ANSATZ_REGISTRY

    def test_ry_present(self):
        assert "ry" in ANSATZ_REGISTRY

    def test_realamplitudes_has_label(self):
        assert "label" in ANSATZ_REGISTRY["realamplitudes"]

    def test_realamplitudes_has_description(self):
        assert "description" in ANSATZ_REGISTRY["realamplitudes"]

    def test_realamplitudes_qiskit_class(self):
        assert ANSATZ_REGISTRY["realamplitudes"]["qiskit_class"] == "RealAmplitudes"

    def test_efficientsu2_qiskit_class(self):
        assert ANSATZ_REGISTRY["efficientsu2"]["qiskit_class"] == "EfficientSU2"

    def test_twolocal_qiskit_class(self):
        assert ANSATZ_REGISTRY["twolocal"]["qiskit_class"] == "TwoLocal"

    def test_all_labels_are_non_empty_strings(self):
        for name, entry in ANSATZ_REGISTRY.items():
            assert isinstance(entry.get("label"), str) and entry["label"].strip() != "", \
                f"Ansatz '{name}' has empty label"

    def test_all_descriptions_are_non_empty_strings(self):
        for name, entry in ANSATZ_REGISTRY.items():
            assert isinstance(entry.get("description"), str) and entry["description"].strip() != "", \
                f"Ansatz '{name}' has empty description"

    def test_all_have_qiskit_class(self):
        for name, entry in ANSATZ_REGISTRY.items():
            assert "qiskit_class" in entry, f"Ansatz '{name}' missing 'qiskit_class'"


class TestOptimizerRegistry:
    def test_registry_is_dict(self):
        assert isinstance(OPTIMIZER_REGISTRY, dict)

    def test_registry_not_empty(self):
        assert len(OPTIMIZER_REGISTRY) > 0

    def test_cobyla_present(self):
        assert "cobyla" in OPTIMIZER_REGISTRY

    def test_spsa_present(self):
        assert "spsa" in OPTIMIZER_REGISTRY

    def test_adam_present(self):
        assert "adam" in OPTIMIZER_REGISTRY

    def test_slsqp_present(self):
        assert "slsqp" in OPTIMIZER_REGISTRY

    def test_cobyla_label_mentions_gradient_free(self):
        label = OPTIMIZER_REGISTRY["cobyla"]["label"].lower()
        assert "gradient" in label

    def test_spsa_label_mentions_stochastic(self):
        label = OPTIMIZER_REGISTRY["spsa"]["label"].lower()
        assert "stochastic" in label

    def test_cobyla_qiskit_class(self):
        assert OPTIMIZER_REGISTRY["cobyla"]["qiskit_class"] == "COBYLA"

    def test_spsa_qiskit_class(self):
        assert OPTIMIZER_REGISTRY["spsa"]["qiskit_class"] == "SPSA"

    def test_adam_qiskit_class(self):
        assert OPTIMIZER_REGISTRY["adam"]["qiskit_class"] == "ADAM"

    def test_slsqp_qiskit_class(self):
        assert OPTIMIZER_REGISTRY["slsqp"]["qiskit_class"] == "SLSQP"

    def test_all_labels_are_non_empty_strings(self):
        for name, entry in OPTIMIZER_REGISTRY.items():
            assert isinstance(entry.get("label"), str) and entry["label"].strip() != "", \
                f"Optimizer '{name}' has empty label"

    def test_all_descriptions_are_non_empty_strings(self):
        for name, entry in OPTIMIZER_REGISTRY.items():
            assert isinstance(entry.get("description"), str) and entry["description"].strip() != "", \
                f"Optimizer '{name}' has empty description"

    def test_all_have_qiskit_class(self):
        for name, entry in OPTIMIZER_REGISTRY.items():
            assert "qiskit_class" in entry, f"Optimizer '{name}' missing 'qiskit_class'"
