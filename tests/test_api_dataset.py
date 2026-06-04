"""
Tests for:
  GET /api/dataset/<name>   — fetch domain dataset metadata + preview
"""


class TestDatasetEndpointFinance:
    def test_returns_200(self, client):
        assert client.get("/api/dataset/finance").status_code == 200

    def test_ok_flag_true(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert j.get("ok") is True

    def test_name_matches_request(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert j["name"] == "finance"

    def test_has_columns_list(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j.get("columns"), list)
        assert len(j["columns"]) > 0

    def test_label_column_is_risk_flag(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert j["label_column"] == "risk_flag"

    def test_feature_columns_non_empty(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j["feature_columns"], list)
        assert len(j["feature_columns"]) == 5

    def test_has_preview(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j.get("preview"), list)

    def test_preview_up_to_8_rows(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert len(j["preview"]) <= 8

    def test_n_rows_positive(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert j.get("n_rows", 0) > 0

    def test_domain_is_finance(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert "finance" in j["domain"].lower()

    def test_description_is_string(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j.get("description"), str)

    def test_has_recommended_settings(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j.get("recommended"), dict)

    def test_has_stats(self, client):
        j = client.get("/api/dataset/finance").get_json()
        assert isinstance(j.get("stats"), dict)

    def test_stats_covers_feature_columns(self, client):
        j = client.get("/api/dataset/finance").get_json()
        for col in j["feature_columns"]:
            assert col in j["stats"], f"Stats missing for column '{col}'"


class TestDatasetEndpointSupplyChain:
    def test_returns_200(self, client):
        assert client.get("/api/dataset/supply_chain").status_code == 200

    def test_ok_flag_true(self, client):
        j = client.get("/api/dataset/supply_chain").get_json()
        assert j.get("ok") is True

    def test_label_column_is_disruption_flag(self, client):
        j = client.get("/api/dataset/supply_chain").get_json()
        assert j["label_column"] == "disruption_flag"

    def test_has_five_feature_columns(self, client):
        j = client.get("/api/dataset/supply_chain").get_json()
        assert len(j["feature_columns"]) == 5

    def test_preview_rows_are_dicts(self, client):
        j = client.get("/api/dataset/supply_chain").get_json()
        for row in j["preview"]:
            assert isinstance(row, dict)


class TestDatasetEndpointHR:
    def test_returns_200(self, client):
        assert client.get("/api/dataset/hr").status_code == 200

    def test_ok_flag_true(self, client):
        j = client.get("/api/dataset/hr").get_json()
        assert j.get("ok") is True

    def test_label_column_is_attrition_flag(self, client):
        j = client.get("/api/dataset/hr").get_json()
        assert j["label_column"] == "attrition_flag"

    def test_domain_contains_human(self, client):
        j = client.get("/api/dataset/hr").get_json()
        assert "human" in j["domain"].lower()

    def test_feature_columns_are_known(self, client):
        j = client.get("/api/dataset/hr").get_json()
        expected = {"overtime_hours", "engagement_score", "years_at_company",
                    "training_hours", "performance_score"}
        assert set(j["feature_columns"]) == expected


class TestDatasetEndpointErrors:
    def test_unknown_dataset_returns_400(self, client):
        assert client.get("/api/dataset/nonexistent_dataset_xyz").status_code == 400

    def test_unknown_dataset_returns_error_message(self, client):
        j = client.get("/api/dataset/nonexistent_dataset_xyz").get_json()
        assert "error" in j

    def test_error_message_mentions_dataset_name(self, client):
        j = client.get("/api/dataset/nonexistent_dataset_xyz").get_json()
        assert "nonexistent_dataset_xyz" in j["error"]
