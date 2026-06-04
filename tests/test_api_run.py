"""
Tests for:
  POST /api/run               — launch async pipeline job
  GET  /api/run/status/<id>   — poll job progress / result
  POST /api/run/batch         — validate batch-spec constraints
"""
import json
import time


class TestRunEndpointValidation:
    def test_empty_body_returns_error_status(self, client):
        # An unparseable body causes werkzeug's JSON parser to raise, which the
        # endpoint catches and re-raises as 500; either 400 or 500 is acceptable.
        resp = client.post("/api/run", data=b"", content_type="application/json")
        assert resp.status_code in (400, 500)

    def test_empty_body_error_message(self, client):
        j = client.post("/api/run", data=b"", content_type="application/json").get_json()
        assert "error" in j

    def test_null_body_returns_400(self, client):
        # JSON null → Python None → app returns {"error": "Empty request body"}, 400
        resp = client.post("/api/run", data=b"null", content_type="application/json")
        assert resp.status_code == 400

    def test_no_dataset_in_spec_still_accepted_async(self, client):
        # Endpoint returns 200 immediately even if spec is incomplete —
        # validation happens inside the background worker thread.
        spec = {"framework": "qiskit"}
        resp = client.post(
            "/api/run",
            data=json.dumps(spec),
            content_type="application/json",
        )
        assert resp.status_code == 200


class TestRunEndpointResponse:
    def test_valid_spec_returns_200(self, client, finance_pipeline_spec):
        resp = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_response_has_job_id(self, client, finance_pipeline_spec):
        j = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert "job_id" in j

    def test_job_id_is_string(self, client, finance_pipeline_spec):
        j = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert isinstance(j["job_id"], str)

    def test_job_id_not_empty(self, client, finance_pipeline_spec):
        j = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert j["job_id"].strip() != ""

    def test_initial_status_is_running(self, client, finance_pipeline_spec):
        j = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert j["status"] == "running"

    def test_request_id_present(self, client, finance_pipeline_spec):
        j = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert "request_id" in j

    def test_two_runs_get_different_job_ids(self, client, finance_pipeline_spec):
        j1 = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        j2 = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()
        assert j1["job_id"] != j2["job_id"]


class TestRunStatusEndpoint:
    def test_unknown_job_id_returns_404(self, client):
        resp = client.get("/api/run/status/this-id-does-not-exist-at-all")
        assert resp.status_code == 404

    def test_unknown_job_returns_error_key(self, client):
        j = client.get("/api/run/status/this-id-does-not-exist-at-all").get_json()
        assert "error" in j

    def test_valid_job_id_returns_200(self, client, finance_pipeline_spec):
        job_id = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()["job_id"]

        resp = client.get(f"/api/run/status/{job_id}")
        assert resp.status_code == 200

    def test_status_field_is_valid_value(self, client, finance_pipeline_spec):
        job_id = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()["job_id"]

        j = client.get(f"/api/run/status/{job_id}").get_json()
        assert j["status"] in {"running", "ok", "error"}

    def test_status_has_progress_field(self, client, finance_pipeline_spec):
        job_id = client.post(
            "/api/run",
            data=json.dumps(finance_pipeline_spec),
            content_type="application/json",
        ).get_json()["job_id"]

        j = client.get(f"/api/run/status/{job_id}").get_json()
        assert "progress" in j


class TestRunBatchValidation:
    def test_not_a_list_returns_400(self, client):
        resp = client.post(
            "/api/run/batch",
            data=json.dumps({"key": "value"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_not_a_list_error_message(self, client):
        j = client.post(
            "/api/run/batch",
            data=json.dumps({"key": "value"}),
            content_type="application/json",
        ).get_json()
        assert "error" in j

    def test_too_few_specs_returns_400(self, client, finance_pipeline_spec):
        resp = client.post(
            "/api/run/batch",
            data=json.dumps([finance_pipeline_spec]),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_too_many_specs_returns_400(self, client, finance_pipeline_spec):
        five_specs = [finance_pipeline_spec] * 5
        resp = client.post(
            "/api/run/batch",
            data=json.dumps(five_specs),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_two_specs_accepted(self, client, finance_pipeline_spec):
        two_specs = [finance_pipeline_spec, finance_pipeline_spec]
        resp = client.post(
            "/api/run/batch",
            data=json.dumps(two_specs),
            content_type="application/json",
        )
        # Returns 200 even if quantum execution fails inside the worker
        assert resp.status_code == 200

    def test_batch_response_has_batch_results(self, client, finance_pipeline_spec):
        two_specs = [finance_pipeline_spec, finance_pipeline_spec]
        j = client.post(
            "/api/run/batch",
            data=json.dumps(two_specs),
            content_type="application/json",
        ).get_json()
        assert "batch_results" in j

    def test_batch_results_length_matches_input(self, client, finance_pipeline_spec):
        two_specs = [finance_pipeline_spec, finance_pipeline_spec]
        j = client.post(
            "/api/run/batch",
            data=json.dumps(two_specs),
            content_type="application/json",
        ).get_json()
        assert len(j["batch_results"]) == 2

    def test_each_batch_result_has_index(self, client, finance_pipeline_spec):
        two_specs = [finance_pipeline_spec, finance_pipeline_spec]
        j = client.post(
            "/api/run/batch",
            data=json.dumps(two_specs),
            content_type="application/json",
        ).get_json()
        for result in j["batch_results"]:
            assert "index" in result

    def test_each_batch_result_has_status(self, client, finance_pipeline_spec):
        two_specs = [finance_pipeline_spec, finance_pipeline_spec]
        j = client.post(
            "/api/run/batch",
            data=json.dumps(two_specs),
            content_type="application/json",
        ).get_json()
        for result in j["batch_results"]:
            assert result.get("status") in {"ok", "error"}
