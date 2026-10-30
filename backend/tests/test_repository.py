"""Tests for repository validation and inspection."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.services.repository_service import RepositoryService, RepositoryValidationError


def test_validate_valid_zip(minimal_zip):
    svc = RepositoryService()
    svc.validate_archive(minimal_zip, "repo.zip")  # should not raise


def test_validate_rejects_traversal_zip(traversal_zip):
    svc = RepositoryService()
    with pytest.raises(RepositoryValidationError, match="unsafe path"):
        svc.validate_archive(traversal_zip, "evil.zip")


def test_validate_rejects_non_zip():
    svc = RepositoryService()
    with pytest.raises(RepositoryValidationError, match="Only ZIP"):
        svc.validate_archive(b"not a zip", "repo.tar.gz")


def test_validate_rejects_oversized(tmp_path):
    # Build a zip just over the 50 MB limit
    large_data = b"x" * (51 * 1024 * 1024)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("big.txt", large_data)
    data = buf.getvalue()
    svc = RepositoryService()
    with pytest.raises(RepositoryValidationError, match="limit"):
        svc.validate_archive(data, "big.zip")


def test_upload_endpoint_valid(client, minimal_zip):
    resp = client.post(
        "/api/v1/repositories/upload",
        files={"file": ("repo.zip", minimal_zip, "application/zip")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "archive_path" in body
    assert body["original_filename"] == "repo.zip"


def test_upload_endpoint_rejects_traversal(client, traversal_zip):
    resp = client.post(
        "/api/v1/repositories/upload",
        files={"file": ("evil.zip", traversal_zip, "application/zip")},
    )
    assert resp.status_code == 422


def test_upload_endpoint_rejects_non_zip(client):
    resp = client.post(
        "/api/v1/repositories/upload",
        files={"file": ("notzip.tar.gz", b"garbage", "application/gzip")},
    )
    assert resp.status_code == 422


def test_list_demos(client):
    resp = client.get("/api/v1/repositories/demos")
    assert resp.status_code == 200
    assert "demos" in resp.json()
