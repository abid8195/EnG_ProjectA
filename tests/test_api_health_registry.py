"""
Tests for:
  GET /api/health
  GET /api/registry
  GET /api/backends
"""


class TestHealthEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/health").status_code == 200

    def test_status_is_ok(self, client):
        j = client.get("/api/health").get_json()
        assert j["status"] == "ok"

    def test_version_field_present(self, client):
        j = client.get("/api/health").get_json()
        assert "version" in j

    def test_version_is_string(self, client):
        j = client.get("/api/health").get_json()
        assert isinstance(j["version"], str)

    def test_version_not_empty(self, client):
        j = client.get("/api/health").get_json()
        assert j["version"].strip() != ""


class TestRegistryEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/registry").status_code == 200

    def test_has_encoders_key(self, client):
        assert "encoders" in client.get("/api/registry").get_json()

    def test_has_ansatze_key(self, client):
        assert "ansatze" in client.get("/api/registry").get_json()

    def test_has_optimizers_key(self, client):
        assert "optimizers" in client.get("/api/registry").get_json()

    def test_has_datasets_key(self, client):
        assert "datasets" in client.get("/api/registry").get_json()

    # ── Encoders ────────────────────────────────────────────────────────────────

    def test_angle_encoder_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "angle" in j["encoders"]

    def test_basis_encoder_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "basis" in j["encoders"]

    def test_iqp_encoder_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "iqp" in j["encoders"]

    def test_every_encoder_has_label(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["encoders"].items():
            assert "label" in entry, f"Encoder '{name}' missing 'label'"

    def test_every_encoder_has_description(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["encoders"].items():
            assert "description" in entry, f"Encoder '{name}' missing 'description'"

    # ── Ansatze ─────────────────────────────────────────────────────────────────

    def test_realamplitudes_ansatz_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "realamplitudes" in j["ansatze"]

    def test_efficientsu2_ansatz_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "efficientsu2" in j["ansatze"]

    def test_twolocal_ansatz_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "twolocal" in j["ansatze"]

    def test_ry_ansatz_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "ry" in j["ansatze"]

    def test_every_ansatz_has_label(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["ansatze"].items():
            assert "label" in entry, f"Ansatz '{name}' missing 'label'"

    # ── Optimizers ──────────────────────────────────────────────────────────────

    def test_cobyla_optimizer_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "cobyla" in j["optimizers"]

    def test_spsa_optimizer_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "spsa" in j["optimizers"]

    def test_adam_optimizer_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "adam" in j["optimizers"]

    def test_slsqp_optimizer_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "slsqp" in j["optimizers"]

    def test_every_optimizer_has_label(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["optimizers"].items():
            assert "label" in entry, f"Optimizer '{name}' missing 'label'"

    def test_every_optimizer_has_description(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["optimizers"].items():
            assert "description" in entry, f"Optimizer '{name}' missing 'description'"

    # ── Domain datasets ─────────────────────────────────────────────────────────

    def test_finance_dataset_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "finance" in j["datasets"]

    def test_supply_chain_dataset_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "supply_chain" in j["datasets"]

    def test_hr_dataset_present(self, client):
        j = client.get("/api/registry").get_json()
        assert "hr" in j["datasets"]

    def test_every_dataset_has_feature_columns(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["datasets"].items():
            assert "feature_columns" in entry, f"Dataset '{name}' missing 'feature_columns'"

    def test_every_dataset_has_label_column(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["datasets"].items():
            assert "label_column" in entry, f"Dataset '{name}' missing 'label_column'"

    def test_every_dataset_has_description(self, client):
        j = client.get("/api/registry").get_json()
        for name, entry in j["datasets"].items():
            assert "description" in entry, f"Dataset '{name}' missing 'description'"


class TestBackendsEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/backends").status_code == 200

    def test_has_backends_list(self, client):
        j = client.get("/api/backends").get_json()
        assert "backends" in j
        assert isinstance(j["backends"], list)

    def test_backends_list_not_empty(self, client):
        j = client.get("/api/backends").get_json()
        assert len(j["backends"]) >= 1

    def test_has_default_key(self, client):
        j = client.get("/api/backends").get_json()
        assert "default" in j

    def test_local_aer_present(self, client):
        j = client.get("/api/backends").get_json()
        providers = [b["provider"] for b in j["backends"]]
        assert "aer" in providers

    def test_local_aer_always_available(self, client):
        j = client.get("/api/backends").get_json()
        aer = next(b for b in j["backends"] if b["provider"] == "aer")
        assert aer["available"] is True

    def test_every_backend_has_provider(self, client):
        j = client.get("/api/backends").get_json()
        for b in j["backends"]:
            assert "provider" in b

    def test_every_backend_has_label(self, client):
        j = client.get("/api/backends").get_json()
        for b in j["backends"]:
            assert "label" in b

    def test_every_backend_has_available_flag(self, client):
        j = client.get("/api/backends").get_json()
        for b in j["backends"]:
            assert isinstance(b.get("available"), bool)

    def test_every_backend_has_note(self, client):
        j = client.get("/api/backends").get_json()
        for b in j["backends"]:
            assert "note" in b
