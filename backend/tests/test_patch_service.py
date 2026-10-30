"""Tests for patch validation and application."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.patch import FilePatch, ProposedPatch
from app.services.patch_service import PatchService


@pytest.fixture
def svc() -> PatchService:
    return PatchService()


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "calc.py").write_text("def add(a, b):\n    return a - b  # BUG: should be +\n")
    return tmp_path


def make_patch(job_id: str, file_path: str, diff: str) -> ProposedPatch:
    return ProposedPatch(
        patch_id="p1",
        job_id=job_id,
        summary="Fix add function.",
        files=[FilePatch(file_path=file_path, unified_diff=diff, change_description="Fix")],
    )


VALID_DIFF = """\
--- a/src/calc.py
+++ b/src/calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b  # BUG: should be +
+    return a + b
"""


def test_validate_valid_patch(svc, sample_repo):
    patch = make_patch("j1", "src/calc.py", VALID_DIFF)
    result = svc.validate_patch(patch, sample_repo)
    assert result.is_valid
    assert result.errors == []


def test_validate_rejects_traversal(svc, sample_repo):
    patch = make_patch("j1", "../../etc/passwd", VALID_DIFF)
    result = svc.validate_patch(patch, sample_repo)
    assert not result.is_valid
    assert any("traversal" in e.lower() or "unsafe" in e.lower() for e in result.errors)


def test_validate_rejects_protected_path(svc, sample_repo):
    patch = make_patch("j1", ".env", VALID_DIFF)
    result = svc.validate_patch(patch, sample_repo)
    assert not result.is_valid
    assert any("protected" in e.lower() for e in result.errors)


def test_validate_rejects_empty_diff(svc, sample_repo):
    patch = make_patch("j1", "src/calc.py", "")
    result = svc.validate_patch(patch, sample_repo)
    assert not result.is_valid


def test_apply_patch_succeeds(svc, sample_repo, tmp_path):
    patch = make_patch("j1", "src/calc.py", VALID_DIFF)
    ws = tmp_path / "workspace"
    success, errors = svc.apply_patch_to_workspace(patch, sample_repo, ws)
    assert success, errors
    patched_content = (ws / "src" / "calc.py").read_text()
    assert "a + b" in patched_content
    assert "a - b" not in patched_content


def test_apply_patch_creates_clean_copy(svc, sample_repo, tmp_path):
    patch = make_patch("j1", "src/calc.py", VALID_DIFF)
    ws = tmp_path / "workspace"
    svc.apply_patch_to_workspace(patch, sample_repo, ws)
    # Original must be unchanged
    original = (sample_repo / "src" / "calc.py").read_text()
    assert "a - b" in original
