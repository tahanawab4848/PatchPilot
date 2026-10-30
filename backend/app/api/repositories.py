"""
Repository upload and inspection endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.database import DbSession
from app.schemas.job import CreateJobRequest, JobStatus
from app.schemas.repository import (
    FileContentRequest,
    FileContentResponse,
    RepoInspectResponse,
    UploadResponse,
)
from app.services.job_service import JobService
from app.services.repository_service import RepositoryService, RepositoryValidationError

router = APIRouter(prefix="/repositories", tags=["repositories"])

_job_svc = JobService()
_repo_svc = RepositoryService()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_repository(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
):
    """
    Accept a ZIP archive upload.
    Returns a storage path that can be used when creating a job.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .zip archives are supported.",
        )

    data = await file.read()

    try:
        svc = RepositoryService(settings)
        svc.validate_archive(data, file.filename)
        archive_path = svc.save_archive(data, file.filename)
    except RepositoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return UploadResponse(
        archive_path=archive_path,
        original_filename=file.filename,
        size_bytes=len(data),
        message="Archive uploaded successfully.",
    )


@router.post("/inspect/{job_id}", response_model=RepoInspectResponse)
async def inspect_repository(
    job_id: str,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    """
    Extract and index the repository associated with a job.
    Updates the job's project_metadata.
    """
    try:
        job = _job_svc.get_job(db, job_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.archive_path:
        raise HTTPException(
            status_code=422,
            detail="Job has no archive path. Upload a repository first.",
        )

    svc = RepositoryService(settings)
    try:
        repo_root = svc.extract_archive(job.archive_path, job_id)
        index = svc.build_index(repo_root)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Repository inspection failed: {exc}")

    # Persist metadata on the job
    _job_svc.set_project_metadata(db, job_id, index.metadata.model_dump())
    _job_svc.update_status(db, job_id, JobStatus.analyzing)

    return RepoInspectResponse(job_id=job_id, index=index)


@router.get("/file/{job_id}", response_model=FileContentResponse)
async def get_file_content(
    job_id: str,
    path: str = Query(..., min_length=1, max_length=1024),
    start_line: int = Query(1, ge=1),
    max_lines: int = Query(200, ge=1, le=2000),
    db: DbSession = None,
    settings: Settings = Depends(get_settings),
):
    """
    Return a bounded excerpt from a repository file.
    Used by the frontend code viewer and agent tool calls.
    """
    repo_root = None
    if db is not None:
        try:
            job = _job_svc.get_job(db, job_id)
            if job.repo_source == "demo":
                here = Path(__file__).resolve().parent
                candidates = [
                    here.parent.parent.parent / "demo_projects" / job.repo_name,
                    Path("./demo_projects") / job.repo_name,
                    Path("../demo_projects") / job.repo_name,
                ]
                repo_root = next((c for c in candidates if c.exists()), None)
        except Exception:
            pass

    if not repo_root:
        ws_root = Path("./workspaces") / job_id
        if ws_root.exists():
            entries = list(ws_root.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                repo_root = entries[0]
            else:
                repo_root = ws_root
        else:
            repo_root = Path("./demo_projects")

    svc = RepositoryService(settings)
    try:
        content, total_lines = svc.read_file_excerpt(repo_root, path, start_line, max_lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    end_line = min(start_line + max_lines - 1, total_lines)
    return FileContentResponse(
        path=path,
        content=content,
        total_lines=total_lines,
        start_line=start_line,
        end_line=end_line,
        language=_detect_language(path),
    )


@router.get("/demos")
async def list_demo_projects():
    """List available bundled demo projects."""
    # Look relative to this file's location (backend/app/api/), go up to project root
    here = Path(__file__).resolve().parent  # app/api
    candidates = [
        here.parent.parent.parent / "demo_projects",  # project root
        Path("./demo_projects"),                        # cwd-relative
        Path("../demo_projects"),                       # one up from backend/
    ]
    demo_root = next((p for p in candidates if p.exists()), None)
    demos = []
    if demo_root:
        for d in demo_root.iterdir():
            if d.is_dir():
                readme = d / "README.md"
                description = ""
                if readme.exists():
                    try:
                        description = readme.read_text(encoding="utf-8")[:300]
                    except OSError:
                        pass
                demos.append({
                    "id": d.name,
                    "name": d.name.replace("_", " ").title(),
                    "description": description,
                    "path": str(d),
                })
    return {"demos": demos}


def _detect_language(path: str) -> Optional[str]:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".go": "go",
        ".rs": "rust", ".rb": "ruby", ".sh": "bash", ".md": "markdown",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    }
    suffix = Path(path).suffix.lower()
    return ext_map.get(suffix)
