"""
RepositoryService: validates, extracts, and indexes repository archives.

Security:
- Rejects path-traversal entries in ZIP files.
- Enforces per-file and total-size limits.
- Skips binary files from content extraction.
- Does NOT execute any code during inspection.
"""

from __future__ import annotations

import io
import mimetypes
import os
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.repository import (
    DependencyManifest,
    FileEntry,
    ProjectMetadata,
    RepositoryIndex,
    TestFrameworkInfo,
)

log = get_logger(__name__)

# ── Allowlists ─────────────────────────────────────────────────────────────────

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".tox", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".cache", "coverage",
    ".pytest_cache", ".mypy_cache", "*.egg-info",
}

BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".ttf", ".woff",
}

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".sh": "Shell",
}

MANIFEST_FILES = {
    "requirements.txt": "requirements.txt",
    "pyproject.toml": "pyproject.toml",
    "setup.py": "setup.py",
    "setup.cfg": "setup.cfg",
    "package.json": "package.json",
    "Cargo.toml": "Cargo.toml",
    "go.mod": "go.mod",
    "Gemfile": "Gemfile",
    "pom.xml": "pom.xml",
}

LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "Cargo.lock", "composer.lock",
}

CONFIG_BUILD_SCRIPTS = {
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml",
    "tsconfig.json", "webpack.config.js", "vite.config.ts", "vite.config.js",
    "CMakeLists.txt", "build.sh", "run.sh",
}

SENSITIVE_PATTERNS = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
}


class RepositoryValidationError(Exception):
    pass


class RepositoryService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._upload_dir = Path("./uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ──────────────────────────────────────────────────────────────

    def validate_archive(self, data: bytes, filename: str) -> None:
        """Raise RepositoryValidationError if the archive is unsafe or too large."""
        if len(data) > self._settings.max_upload_bytes:
            raise RepositoryValidationError(
                f"Archive exceeds {self._settings.max_upload_size_mb} MB limit."
            )
        if not (filename.endswith(".zip")):
            raise RepositoryValidationError("Only ZIP archives are supported.")
        self._check_zip_safety(data)

    def save_archive(self, data: bytes, original_filename: str) -> str:
        """Persist the archive and return its relative storage path."""
        safe_name = uuid.uuid4().hex + ".zip"
        dest = self._upload_dir / safe_name
        dest.write_bytes(data)
        log.info("archive_saved", path=str(dest), original=original_filename)
        return str(dest)

    def extract_archive(self, archive_path: str, job_id: str) -> Path:
        """Extract the archive to an isolated working directory and return the root path."""
        work_root = Path("./workspaces") / job_id
        work_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as zf:
            for member in zf.infolist():
                self._safe_extract_member(zf, member, work_root)
        # Collapse single top-level wrapper dir (common in GitHub ZIPs)
        entries = list(work_root.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return work_root

    def build_index(self, repo_root: Path) -> RepositoryIndex:
        """Walk the repository and build a FileEntry list and ProjectMetadata."""
        files: list[FileEntry] = []
        languages: dict[str, int] = {}
        manifests: list[DependencyManifest] = []
        test_files: list[str] = []
        lockfiles: list[str] = []
        config_scripts: list[str] = []
        sensitive_files: list[str] = []
        dangerous_configs: list[str] = []
        oversized_skipped = 0
        binary_skipped = 0

        for abs_path in self._walk(repo_root):
            rel = abs_path.relative_to(repo_root)
            rel_str = str(rel).replace("\\", "/")
            ext = abs_path.suffix.lower()
            basename = abs_path.name
            size = abs_path.stat().st_size
            is_binary = ext in BINARY_EXTENSIONS

            # Check for symlink escaping root
            if abs_path.is_symlink():
                try:
                    resolved_target = abs_path.resolve()
                    resolved_target.relative_to(repo_root.resolve())
                except ValueError:
                    dangerous_configs.append(
                        f"Symlink {rel_str} escapes repository root pointing to {abs_path.resolve()}"
                    )
                    continue

            # Check sensitive files
            if basename in SENSITIVE_PATTERNS or basename.startswith(".env") or ext in (".pem", ".key", ".p12"):
                sensitive_files.append(rel_str)

            # Check lockfiles
            if basename in LOCKFILES:
                lockfiles.append(rel_str)

            # Check configuration / build scripts
            if basename in CONFIG_BUILD_SCRIPTS or basename.endswith(".config.js") or basename.endswith(".config.ts"):
                config_scripts.append(rel_str)

            if is_binary:
                binary_skipped += 1
                continue
            if size > self._settings.max_file_bytes:
                oversized_skipped += 1
                continue

            lang = LANGUAGE_EXTENSIONS.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            entry = FileEntry(
                path=rel_str,
                size_bytes=size,
                is_binary=False,
                language=lang,
            )
            files.append(entry)

            # Detect test files
            if self._is_test_file(rel_str):
                test_files.append(rel_str)

            # Detect manifests
            if basename in MANIFEST_FILES:
                try:
                    raw = abs_path.read_text(encoding="utf-8", errors="replace")[:4000]
                except OSError:
                    raw = None
                manifests.append(DependencyManifest(
                    path=rel_str,
                    kind=MANIFEST_FILES[basename],
                    raw_content=raw,
                ))

        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_langs[0][0] if sorted_langs else None

        test_frameworks = self._detect_test_frameworks(files, manifests, repo_root)
        entry_points = self._detect_entry_points(files)
        relevant = self._score_relevant_files(files, test_files)

        metadata = ProjectMetadata(
            detected_languages=[l for l, _ in sorted_langs],
            primary_language=primary,
            frameworks=self._detect_frameworks(files, manifests),
            test_frameworks=test_frameworks,
            entry_points=entry_points,
            manifests=manifests,
            lockfiles=lockfiles,
            configuration_and_build_scripts=config_scripts,
            sensitive_files=sensitive_files,
            dangerous_configurations=dangerous_configs,
            total_files=len(files),
            source_files=len(files) - len(test_files),
            test_files=len(test_files),
            oversized_files_skipped=oversized_skipped,
            binary_files_skipped=binary_skipped,
        )

        return RepositoryIndex(
            files=files,
            relevant_files=relevant,
            test_files=test_files,
            metadata=metadata,
        )

    def read_file_excerpt(
        self, repo_root: Path, rel_path: str, start_line: int = 1, max_lines: int = 200
    ) -> Tuple[str, int]:
        """
        Read a bounded excerpt from a file within the repository.
        Returns (content, total_lines). Raises ValueError on unsafe paths.
        """
        safe_path = self._resolve_safe_path(repo_root, rel_path)
        lines = safe_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        total = len(lines)
        start_idx = max(0, start_line - 1)
        chunk = lines[start_idx: start_idx + max_lines]
        return "".join(chunk), total

    def cleanup_workspace(self, job_id: str) -> None:
        ws = Path("./workspaces") / job_id
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _check_zip_safety(self, data: bytes) -> None:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if self._is_traversal_path(info.filename):
                    raise RepositoryValidationError(
                        f"ZIP entry has unsafe path: {info.filename!r}"
                    )
                if info.file_size > self._settings.max_file_bytes * 10:
                    # Allow up to 10x per-file limit inside archive for compressed data
                    raise RepositoryValidationError(
                        f"ZIP entry too large: {info.filename!r} ({info.file_size} bytes)"
                    )

    def _is_traversal_path(self, name: str) -> bool:
        # Reject absolute paths and any that escape via ..
        p = PurePosixPath(name)
        if p.is_absolute():
            return True
        parts = name.replace("\\", "/").split("/")
        for part in parts:
            if part in ("..", ""):
                return True
        return False

    def _safe_extract_member(
        self, zf: zipfile.ZipFile, member: zipfile.ZipInfo, dest: Path
    ) -> None:
        name = member.filename.replace("\\", "/")
        if self._is_traversal_path(name):
            return
        target = dest / name
        # Ensure the resolved path stays within dest
        try:
            target.resolve().relative_to(dest.resolve())
        except ValueError:
            return
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)

    def _walk(self, root: Path):
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune skip dirs in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in SKIP_DIRS and not d.endswith(".egg-info")
            ]
            for fname in filenames:
                yield Path(dirpath) / fname

    def _is_test_file(self, rel: str) -> bool:
        parts = rel.lower().split("/")
        name = parts[-1]
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith("_test.go")
            or name.endswith(".test.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.js")
            or name.endswith(".spec.ts")
            or name.endswith(".test.jsx")
            or name.endswith(".test.tsx")
            or name.endswith(".spec.jsx")
            or name.endswith(".spec.tsx")
            or "tests/" in rel.lower()
            or "test/" in rel.lower()
            or "__tests__/" in rel.lower()
            or name in ("conftest.py",)
        )

    def _detect_test_frameworks(
        self, files: list[FileEntry], manifests: list[DependencyManifest], root: Path
    ) -> list[TestFrameworkInfo]:
        result = []
        file_paths = {f.path for f in files}
        all_manifest_content = " ".join(
            (m.raw_content or "") for m in manifests
        ).lower()

        # ── Python / pytest ──────────────────────────────────────────────────────
        has_python_tests = any(
            self._is_test_file(f.path) and f.path.endswith(".py")
            for f in files
        )
        if has_python_tests:
            config_file = next(
                (p for p in ("pytest.ini", "pyproject.toml", "setup.cfg") if p in file_paths),
                None,
            )
            result.append(TestFrameworkInfo(
                name="pytest",
                config_file=config_file,
                test_command="python -m pytest -v --tb=short",
                test_dirs=["tests", "test"],
            ))

        # ── JavaScript / TypeScript — Jest ───────────────────────────────────────
        has_js_tests = any(
            self._is_test_file(f.path) and f.path.endswith((".js", ".ts", ".jsx", ".tsx"))
            for f in files
        )
        has_jest = "jest" in all_manifest_content or "jest.config" in " ".join(file_paths)
        has_vitest = "vitest" in all_manifest_content
        has_package_json = "package.json" in file_paths

        if has_js_tests or (has_jest and has_package_json):
            if has_vitest:
                result.append(TestFrameworkInfo(
                    name="vitest",
                    config_file=next(
                        (p for p in ("vitest.config.ts", "vitest.config.js") if p in file_paths),
                        None,
                    ),
                    test_command="npx vitest run --reporter=json",
                    test_dirs=["src", "tests", "__tests__"],
                ))
            else:
                result.append(TestFrameworkInfo(
                    name="jest",
                    config_file=next(
                        (p for p in ("jest.config.js", "jest.config.ts", "jest.config.json") if p in file_paths),
                        None,
                    ),
                    test_command="npx jest --json",
                    test_dirs=["src", "tests", "__tests__"],
                ))

        # ── Go — go test ─────────────────────────────────────────────────────────
        has_go_tests = any(
            self._is_test_file(f.path) and f.path.endswith(".go")
            for f in files
        )
        has_go_mod = "go.mod" in file_paths
        if has_go_tests or has_go_mod:
            result.append(TestFrameworkInfo(
                name="go_test",
                config_file="go.mod" if has_go_mod else None,
                test_command="go test -json ./...",
                test_dirs=["."],
            ))

        # ── Rust — cargo test ────────────────────────────────────────────────────
        has_cargo = "Cargo.toml" in file_paths
        if has_cargo:
            result.append(TestFrameworkInfo(
                name="cargo_test",
                config_file="Cargo.toml",
                test_command="cargo test -- --format json",
                test_dirs=["src", "tests"],
            ))

        return result

    def _detect_frameworks(
        self, files: list[FileEntry], manifests: list[DependencyManifest]
    ) -> list[str]:
        frameworks = []
        all_manifest_content = " ".join(
            (m.raw_content or "") for m in manifests
        ).lower()
        file_paths = {f.path for f in files}

        # Python web frameworks
        if "fastapi" in all_manifest_content:
            frameworks.append("FastAPI")
        if "flask" in all_manifest_content:
            frameworks.append("Flask")
        if "django" in all_manifest_content:
            frameworks.append("Django")
        if "pytest" in all_manifest_content:
            frameworks.append("pytest")

        # JavaScript / TypeScript frameworks
        if "next" in all_manifest_content or any(
            f.path in ("next.config.js", "next.config.ts", "next.config.mjs") for f in files
        ):
            frameworks.append("Next.js")
        if "react" in all_manifest_content and "next" not in all_manifest_content:
            frameworks.append("React")
        if "vue" in all_manifest_content:
            frameworks.append("Vue")
        if "express" in all_manifest_content:
            frameworks.append("Express")
        if "vitest" in all_manifest_content:
            frameworks.append("Vitest")
        elif "jest" in all_manifest_content:
            frameworks.append("Jest")

        # Go
        if "go.mod" in file_paths:
            frameworks.append("Go modules")

        # Rust
        if "Cargo.toml" in file_paths:
            frameworks.append("Cargo")

        return frameworks

    def _detect_entry_points(self, files: list[FileEntry]) -> list[str]:
        candidates = ["main.py", "app.py", "run.py", "server.py", "index.py", "__main__.py"]
        return [f.path for f in files if f.path.split("/")[-1] in candidates]

    def _score_relevant_files(
        self, files: list[FileEntry], test_files: list[str]
    ) -> list[str]:
        """Return source files sorted by estimated relevance (no binary/test)."""
        source = [
            f.path for f in files
            if not f.is_binary and f.path not in test_files and f.language is not None
        ]
        return source[:50]

    def _resolve_safe_path(self, repo_root: Path, rel_path: str) -> Path:
        """Resolve rel_path inside repo_root; raise ValueError if it escapes."""
        clean = rel_path.lstrip("/").replace("\\", "/")
        candidate = (repo_root / clean).resolve()
        if not str(candidate).startswith(str(repo_root.resolve())):
            raise ValueError(f"Path traversal rejected: {rel_path!r}")
        if not candidate.exists():
            raise FileNotFoundError(f"File not found: {rel_path!r}")
        return candidate
