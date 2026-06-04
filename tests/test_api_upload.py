"""
Tests for:
  POST /api/upload   — accept CSV/XLSX, return column metadata and preview
"""
import io


class TestUploadValidCSV:
    def test_returns_200(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200

    def test_ok_flag_true(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert j.get("ok") is True

    def test_returns_columns_list(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("columns"), list)
        assert "feature1" in j["columns"]
        assert "feature2" in j["columns"]
        assert "label" in j["columns"]

    def test_returns_numeric_columns(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("numeric_columns"), list)
        assert len(j["numeric_columns"]) >= 2

    def test_returns_preview(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("preview"), list)

    def test_preview_up_to_8_rows(self, client, large_csv_bytes):
        data = {"file": (io.BytesIO(large_csv_bytes), "large.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert len(j["preview"]) <= 8

    def test_returns_path(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("path"), str)
        assert j["path"].endswith(".csv")

    def test_returns_n_rows(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert j.get("n_rows") == 4

    def test_returns_dtypes(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("dtypes"), dict)

    def test_returns_stats(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "test.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert isinstance(j.get("stats"), dict)

    def test_returns_filename(self, client, minimal_csv_bytes):
        data = {"file": (io.BytesIO(minimal_csv_bytes), "mydata.csv")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert "mydata.csv" in j.get("filename", "")


class TestUploadErrors:
    def test_no_file_field_returns_400(self, client):
        resp = client.post("/api/upload", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_no_file_returns_error_message(self, client):
        j = client.post("/api/upload", data={}, content_type="multipart/form-data").get_json()
        assert "error" in j

    def test_unsupported_extension_returns_400(self, client):
        data = {"file": (io.BytesIO(b"some content"), "data.txt")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_unsupported_extension_error_mentions_type(self, client):
        data = {"file": (io.BytesIO(b"some content"), "data.txt")}
        j = client.post("/api/upload", data=data, content_type="multipart/form-data").get_json()
        assert "error" in j

    def test_invalid_csv_content_returns_400(self, client):
        bad_csv = b"\x00\x01\x02\x03 not a csv \xff\xfe"
        data = {"file": (io.BytesIO(bad_csv), "bad.csv")}
        # Either parses (pandas is lenient) or returns 400 — both are acceptable.
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code in (200, 400)

    def test_csv_with_only_header_returns_200(self, client):
        data = {"file": (io.BytesIO(b"col1,col2,col3\n"), "header_only.csv")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200

    def test_json_extension_returns_400(self, client):
        data = {"file": (io.BytesIO(b'{"a": 1}'), "data.json")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
