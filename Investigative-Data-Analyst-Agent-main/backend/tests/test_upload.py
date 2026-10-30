"""
Tests for dataset upload, listing, retrieval, and deletion endpoints.
"""
import io
import json
import os

import pytest

# ---------------------------------------------------------------------------
# Helpers to build in-memory CSV payloads
# ---------------------------------------------------------------------------

def _csv_bytes(content: str = None) -> bytes:
    """Return CSV content as bytes."""
    if content is None:
        content = "id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n"
    return content.encode("utf-8")


def _make_csv_upload(content: bytes = None, filename: str = "test.csv"):
    """Return a multipart files dict suitable for httpx TestClient."""
    if content is None:
        content = _csv_bytes()
    return {"file": (filename, io.BytesIO(content), "text/csv")}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUploadDataset:
    def test_upload_csv_file(self, client):
        """Uploading a valid CSV returns 201 with correct schema metadata."""
        files = _make_csv_upload()
        response = client.post("/api/datasets/upload", files=files)

        assert response.status_code == 201, response.text
        data = response.json()

        assert data["filename"] == "test.csv"
        assert data["file_type"] == "csv"
        assert data["row_count"] == 3
        assert data["column_count"] == 3
        assert isinstance(data["schema_info"], dict)
        assert "id" in data["schema_info"]
        assert "name" in data["schema_info"]
        assert "value" in data["schema_info"]
        assert data["file_size_bytes"] > 0

    def test_upload_invalid_type(self, client):
        """Uploading a .txt file returns HTTP 400."""
        files = {"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")}
        response = client.post("/api/datasets/upload", files=files)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_xlsx_file(self, client, tmp_path):
        """Uploading a valid XLSX returns 201."""
        import pandas as pd

        xlsx_path = tmp_path / "data.xlsx"
        df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
        df.to_excel(str(xlsx_path), index=False)

        with open(str(xlsx_path), "rb") as fh:
            files = {"file": ("data.xlsx", fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            response = client.post("/api/datasets/upload", files=files)

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["file_type"] == "xlsx"
        assert data["row_count"] == 2


class TestListDatasets:
    def test_list_datasets_empty(self, client):
        """GET /datasets/ on empty DB returns total=0."""
        response = client.get("/api/datasets/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["datasets"] == []

    def test_list_datasets_after_uploads(self, client):
        """Upload two CSVs, then GET / asserts count == 2."""
        csv1 = _csv_bytes("a,b\n1,2\n3,4\n")
        csv2 = _csv_bytes("x,y,z\n10,20,30\n")

        client.post("/api/datasets/upload", files=_make_csv_upload(csv1, "file1.csv"))
        client.post("/api/datasets/upload", files=_make_csv_upload(csv2, "file2.csv"))

        response = client.get("/api/datasets/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["datasets"]) == 2


class TestGetDataset:
    def test_get_dataset_by_id(self, client):
        """Upload a file, then GET /{id} returns the same record."""
        upload_resp = client.post(
            "/api/datasets/upload",
            files=_make_csv_upload(_csv_bytes(), "lookup.csv"),
        )
        assert upload_resp.status_code == 201
        dataset_id = upload_resp.json()["id"]

        get_resp = client.get(f"/api/datasets/{dataset_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == dataset_id
        assert data["filename"] == "lookup.csv"

    def test_get_nonexistent_dataset(self, client):
        """GET /{id} for a missing dataset returns 404."""
        response = client.get("/api/datasets/99999")
        assert response.status_code == 404


class TestDeleteDataset:
    def test_delete_dataset(self, client):
        """Upload a dataset, delete it, confirm 404 on subsequent GET."""
        upload_resp = client.post(
            "/api/datasets/upload",
            files=_make_csv_upload(_csv_bytes(), "delete_me.csv"),
        )
        assert upload_resp.status_code == 201
        dataset_id = upload_resp.json()["id"]

        delete_resp = client.delete(f"/api/datasets/{dataset_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/api/datasets/{dataset_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_dataset(self, client):
        """DELETE /{id} for a missing dataset returns 404."""
        response = client.delete("/api/datasets/99999")
        assert response.status_code == 404
