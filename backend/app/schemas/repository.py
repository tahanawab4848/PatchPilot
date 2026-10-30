"""
Repository analysis schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    path: str
    size_bytes: int
    is_binary: bool = False
    language: Optional[str] = None


class DependencyManifest(BaseModel):
    path: str
    kind: str  # e.g. "requirements.txt", "pyproject.toml", "package.json"
    raw_content: Optional[str] = None


class TestFrameworkInfo(BaseModel):
    name: str          # e.g. "pytest", "unittest", "jest"
    config_file: Optional[str] = None
    test_command: Optional[str] = None
    test_dirs: List[str] = []


class ProjectMetadata(BaseModel):
    detected_languages: List[str] = []
    primary_language: Optional[str] = None
    frameworks: List[str] = []
    test_frameworks: List[TestFrameworkInfo] = []
    entry_points: List[str] = []
    manifests: List[DependencyManifest] = []
    lockfiles: List[str] = []
    configuration_and_build_scripts: List[str] = []
    sensitive_files: List[str] = []
    dangerous_configurations: List[str] = []
    total_files: int = 0
    source_files: int = 0
    test_files: int = 0
    oversized_files_skipped: int = 0
    binary_files_skipped: int = 0


class RepositoryIndex(BaseModel):
    files: List[FileEntry] = []
    relevant_files: List[str] = []
    test_files: List[str] = []
    metadata: ProjectMetadata


class UploadResponse(BaseModel):
    archive_path: str
    original_filename: str
    size_bytes: int
    message: str


class FileContentRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024)
    max_lines: int = Field(200, ge=1, le=2000)
    start_line: int = Field(1, ge=1)


class FileContentResponse(BaseModel):
    path: str
    content: str
    total_lines: int
    start_line: int
    end_line: int
    language: Optional[str] = None


class RepoInspectResponse(BaseModel):
    job_id: str
    index: RepositoryIndex
