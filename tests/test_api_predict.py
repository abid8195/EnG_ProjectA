"""
Tests for:
  POST /api/predict  — run predictions with a saved model

Most predict tests exercise the validation / error paths because a real
trained model requires the full quantum stack.  The model-not-found test
is independent of Qiskit.
"""
import json


class TestPredictValidation:
    def test_missing_model_id_returns_400(self, client):
        body = {"path": "datasets/finance_portfolio_risk.csv"}
        resp = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_model_id_error_message(self, client):
        body = {"path": "datasets/finance_portfolio_risk.csv"}
        j = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        ).get_json()
        assert "error" in j
        assert "model_id" in j["error"].lower()

    def test_missing_path_returns_400(self, client):
        body = {"model_id": "some_model_id"}
        resp = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_path_error_message(self, client):
        body = {"model_id": "some_model_id"}
        j = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        ).get_json()
        assert "error" in j
        assert "path" in j["error"].lower()

    def test_nonexistent_model_returns_404(self, client):
        body = {
            "model_id": "nonexistent_model_id_xyz123",
            "path": "datasets/finance_portfolio_risk.csv",
            "feature_columns": ["market_volatility", "debt_ratio"],
        }
        resp = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_nonexistent_model_error_message(self, client):
        body = {
            "model_id": "nonexistent_model_id_xyz123",
            "path": "datasets/finance_portfolio_risk.csv",
            "feature_columns": ["market_volatility"],
        }
        j = client.post(
            "/api/predict",
            data=json.dumps(body),
            content_type="application/json",
        ).get_json()
        assert "error" in j

    def test_empty_body_still_returns_error(self, client):
        j = client.post(
            "/api/predict",
            data=json.dumps({}),
            content_type="application/json",
        ).get_json()
        assert "error" in j
