"""
PatchService: validates and applies unified diffs.

Security:
- Validates that all patched paths stay within the repository root.
- Rejects oversized or multi-file diffs beyond the allowed limit.
- Never executes shell commands; uses Python-level diff application.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.schemas.patch import FilePatch, PatchValidationResult, ProposedPatch

log = get_logger(__name__)

MAX_PATCH_FILES = 20
MAX_DIFF_BYTES = 100_000  # 100 KB

# Protected paths that must never be modified by a generated patch.
PROTECTED_PATHS = {
    ".env", ".env.example", "Dockerfile", "docker-compose.yml",
    ".git", ".github",
}


class PatchService:
    def validate_patch(
        self, patch: ProposedPatch, repo_root: Path
    ) -> PatchValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if len(patch.files) > MAX_PATCH_FILES:
            errors.append(
                f"Patch modifies {len(patch.files)} files; maximum is {MAX_PATCH_FILES}."
            )

        total_diff_bytes = sum(len(fp.unified_diff.encode()) for fp in patch.files)
        if total_diff_bytes > MAX_DIFF_BYTES:
            errors.append(
                f"Patch diff is {total_diff_bytes} bytes; maximum is {MAX_DIFF_BYTES}."
            )

        for fp in patch.files:
            path_errors = self._validate_file_path(fp.file_path, repo_root)
            errors.extend(path_errors)
            if not fp.unified_diff.strip():
                errors.append(f"Empty diff for file: {fp.file_path!r}")
            elif not self._looks_like_unified_diff(fp.unified_diff):
                errors.append(
                    f"Diff for {fp.file_path!r} does not contain valid unified diff syntax (missing @@ header)."
                )
            # Check for suspicious unsafe code injection in added diff lines
            for line in fp.unified_diff.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added = line[1:].strip()
                    if any(susp in added for susp in ["os.system(", "subprocess.Popen(", "subprocess.call(", "__import__('os')"]):
                        warnings.append(
                            f"Patch introduces execution call in {fp.file_path!r}: {added[:60]}"
                        )

        return PatchValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def apply_patch_to_workspace(
        self,
        patch: ProposedPatch,
        original_root: Path,
        workspace_root: Path,
    ) -> Tuple[bool, List[str]]:
        """
        Copy the original repo to a new workspace and apply the patch there.
        Returns (success, list_of_errors).
        """
        errors: List[str] = []

        # Create a clean copy of the repo
        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        shutil.copytree(original_root, workspace_root)

        for fp in patch.files:
            success, err = self._apply_file_patch(fp, workspace_root)
            if not success:
                errors.append(err or f"Failed to apply patch to {fp.file_path!r}")

        return len(errors) == 0, errors

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _validate_file_path(self, rel_path: str, repo_root: Path) -> List[str]:
        errors = []
        clean = rel_path.lstrip("/").replace("\\", "/")
        parts = clean.split("/")

        for part in parts:
            if part in ("..", ""):
                errors.append(f"Path traversal in patch path: {rel_path!r}")
                return errors

        top_level = parts[0] if parts else ""
        if top_level in PROTECTED_PATHS or clean in PROTECTED_PATHS:
            errors.append(f"Patch targets a protected path: {rel_path!r}")

        # Verify the path would resolve inside the repo
        try:
            candidate = (repo_root / clean).resolve()
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"Patch path escapes repository root: {rel_path!r}")

        return errors

    def _looks_like_unified_diff(self, diff: str) -> bool:
        return "@@" in diff and (
            diff.lstrip().startswith("---")
            or diff.lstrip().startswith("+++")
            or diff.lstrip().startswith("diff ")
            or "@@" in diff[:500]
        )

    def _apply_file_patch(
        self, fp: FilePatch, workspace_root: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Apply a single file's unified diff.
        Uses a pure-Python patch implementation to avoid shell execution.
        """
        clean_path = fp.file_path.lstrip("/").replace("\\", "/")
        target = workspace_root / clean_path

        try:
            # Read original content (file may not exist for new-file patches)
            if target.exists():
                original_lines = target.read_text(encoding="utf-8", errors="replace").splitlines(
                    keepends=True
                )
            else:
                original_lines = []

            patched_lines = self._apply_unified_diff(original_lines, fp.unified_diff)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("".join(patched_lines), encoding="utf-8")
            log.info("patch_applied", path=clean_path)
            return True, None
        except Exception as exc:
            log.error("patch_apply_failed", path=clean_path, error=str(exc))
            return False, str(exc)

    def _apply_unified_diff(
        self, original_lines: List[str], diff_text: str
    ) -> List[str]:
        """
        Minimal unified-diff application.
        Handles standard hunks produced by difflib / git diff.
        """
        # Parse hunks
        hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        diff_lines = diff_text.splitlines(keepends=True)

        result: List[str] = list(original_lines)
        offset = 0  # tracks how many lines we have inserted/deleted so far
        i = 0

        while i < len(diff_lines):
            line = diff_lines[i]
            m = hunk_re.match(line)
            if not m:
                i += 1
                continue

            orig_start = int(m.group(1))
            orig_len = int(m.group(2)) if m.group(2) is not None else 1
            new_len = int(m.group(4)) if m.group(4) is not None else 1

            i += 1
            hunk_remove: List[str] = []
            hunk_add: List[str] = []

            while i < len(diff_lines) and not hunk_re.match(diff_lines[i]):
                hline = diff_lines[i]
                if hline.startswith("-"):
                    hunk_remove.append(hline[1:])
                elif hline.startswith("+"):
                    hunk_add.append(hline[1:])
                elif hline.startswith(" "):
                    hunk_remove.append(hline[1:])
                    hunk_add.append(hline[1:])
                elif hline.startswith("\\ No newline"):
                    pass  # ignore no-newline markers
                i += 1

            # Apply: find the position in result (1-indexed orig_start + offset)
            apply_at = orig_start - 1 + offset
            apply_at = max(0, min(apply_at, len(result)))

            # Fuzzy match fallback: if the lines at apply_at don't match hunk_remove,
            # search for the closest matching position in result.
            if hunk_remove and result:
                target_block = [l.strip() for l in hunk_remove if l.strip()]
                if target_block:
                    first_line = target_block[0]
                    # Check if exact match at apply_at
                    curr_block = [l.strip() for l in result[apply_at: apply_at + len(hunk_remove)] if l.strip()]
                    if curr_block != target_block:
                        # Search near apply_at
                        best_pos = None
                        min_dist = 9999
                        for pos in range(len(result)):
                            if result[pos].strip() == first_line:
                                dist = abs(pos - apply_at)
                                if dist < min_dist:
                                    min_dist = dist
                                    best_pos = pos
                        if best_pos is not None and min_dist < 50:
                            apply_at = best_pos

            # Replace hunk_remove lines with hunk_add lines
            result[apply_at: apply_at + orig_len] = hunk_add
            offset += len(hunk_add) - orig_len

        return result
