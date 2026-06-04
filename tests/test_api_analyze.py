"""
Tests for:
  POST /api/analyze  — return missing-value counts and class-balance info
"""
import io
import json


FINANCE_PATH = "datasets/finance_portfolio_risk.csv"
FINANCE_LABEL = "risk_flag"
FINANCE_FEATURES = ["market_volatility", "debt_ratio"]


class TestAnalyzeErrors:
    def test_missing_path_returns_400(self, client):
        resp = client.post(
            "/api/analyze",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_path_error_message(self, client):
        j = client.post(
            "/api/analyze",
            data=json.dumps({}),
            content_type="application/json",
        ).get_json()
        assert "error" in j

    def test_nonexistent_file_returns_404(self, client):
        body = {"path": "nonexistent/totally_missing_file.csv"}
        resp = client.post(
            "/api/analyze",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_nonexistent_file_error_message(self, client):
        body = {"path": "nonexistent/totally_missing_file.csv"}
        j = client.post(
            "/api/analyze",
            data=json.dumps(body),
            content_type="application/json",
        ).get_json()
        assert "error" in j


class TestAnalyzeValidDataset:
    def _post(self, client, extra=None):
        body = {
            "path": FINANCE_PATH,
            "label_column": FINANCE_LABEL,
            "feature_columns": FINANCE_FEATURES,
        }
        if extra:
            body.update(extra)
        return client.post(
            "/api/analyze",
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_returns_200(self, client):
        assert self._post(client).status_code == 200

    def test_ok_flag_true(self, client):
        j = self._post(client).get_json()
        assert j.get("ok") is True

    def test_returns_n_rows(self, client):
        j = self._post(client).get_json()
        assert j.get("n_rows", 0) > 0

    def test_returns_missing_counts(self, client):
        j = self._post(client).get_json()
        assert isinstance(j.get("missing_counts"), dict)

    def test_missing_counts_covers_checked_columns(self, client):
        j = self._post(client).get_json()
        for col in [FINANCE_LABEL] + FINANCE_FEATURES:
            assert col in j["missing_counts"], f"missing_counts missing column '{col}'"

    def test_returns_class_balance(self, client):
        j = self._post(client).get_json()
        assert j.get("class_balance") is not None

    def test_class_balance_has_value_counts(self, client):
        j = self._post(client).get_json()
        assert "value_counts" in j["class_balance"]

    def test_class_balance_has_n_rows(self, client):
        j = self._post(client).get_json()
        assert "n_rows" in j["class_balance"]

    def test_returns_columns_list(self, client):
        j = self._post(client).get_json()
        assert isinstance(j.get("columns"), list)
        assert len(j["columns"]) > 0

    def test_returns_numeric_columns(self, client):
        j = self._post(client).get_json()
        assert isinstance(j.get("numeric_columns"), list)

    def test_returns_stats(self, client):
        j = self._post(client).get_json()
        assert isinstance(j.get("stats"), dict)

    def test_no_label_column_still_returns_200(self, client):
        body = {"path": FINANCE_PATH, "feature_columns": FINANCE_FEATURES}
        resp = client.post(
            "/api/analyze",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_no_label_column_class_balance_is_none(self, client):
        body = {"path": FINANCE_PATH, "feature_columns": FINANCE_FEATURES}
        j = client.post(
            "/api/analyze",
            data=json.dumps(body),
            content_type="application/json",
        ).get_json()
        assert j.get("class_balance") is None
