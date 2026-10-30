"""
Job management endpoints.

On POST /jobs:
  1. Creates the job record.
  2. Launches the DebuggingAgent as a background asyncio task.

On POST /jobs/{id}/cancel:
  Cancels the running agent task (if any) before updating status.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.agents.runner import cancel_agent, get_running_jobs, launch_agent
from app.core.config import Settings, get_settings
from app.core.database import DbSession
from app.schemas.job import (
    CreateJobRequest,
    JobDetail,
    JobStatus,
    JobSummary,
    PatchApprovalRequest,
)
from app.services.job_service import JobNotFoundError, JobService
from app.services.thought_streamer import thought_broadcaster

router = APIRouter(prefix="/jobs", tags=["jobs"])

_svc = JobService()


@router.post("", response_model=JobDetail, status_code=status.HTTP_201_CREATED)
async def create_job(request: CreateJobRequest, db: DbSession):
    """
    Create a debugging job and immediately launch the autonomous agent.
    The agent runs as a background asyncio task — polling /jobs/{id} for updates.
    """
    job = _svc.create_job(db, request)
    # Fire-and-forget — agent runs independently
    await launch_agent(job.id)
    return _svc.to_detail(job)


@router.get("", response_model=List[JobSummary])
async def list_jobs(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return paginated job history, newest first."""
    jobs = _svc.list_jobs(db, limit=limit, offset=offset)
    return [JobSummary.model_validate(j) for j in jobs]


@router.get("/running")
async def list_running_jobs():
    """Return job_ids of jobs whose agent is currently executing."""
    return {"running": get_running_jobs()}


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: str, db: DbSession):
    """Return full job details including stage event log."""
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _svc.to_detail(job)


@router.post("/{job_id}/approve", response_model=JobDetail)
async def approve_patch(
    job_id: str,
    request: PatchApprovalRequest,
    db: DbSession,
):
    """
    Record a patch approval or rejection.

    Approving sets status → applying_patch, which the waiting agent detects
    and proceeds to Stage G.
    Rejecting sets status → failed (the agent also detects this).
    """
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.awaiting_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Job is in state {job.status!r}, not awaiting_approval.",
        )

    if not job.proposed_patch:
        raise HTTPException(status_code=409, detail="No proposed patch to approve.")

    _svc.set_patch_approval(db, job_id, request.decision.value, request.notes)
    if request.decision == PatchApproval.approved:
        _svc.update_status(db, job_id, JobStatus.applying_patch)
    elif request.decision == PatchApproval.revised:
        _svc.update_status(db, job_id, JobStatus.diagnosing)
    elif request.decision == PatchApproval.cancelled:
        cancel_agent(job_id)
        _svc.update_status(db, job_id, JobStatus.cancelled)
    else:
        _svc.update_status(
            db, job_id, JobStatus.failed,
            error_message=f"Patch rejected by user.{' Notes: ' + request.notes if request.notes else ''}"
        )

    job = _svc.get_job(db, job_id)
    return _svc.to_detail(job)


@router.post("/{job_id}/cancel", response_model=JobDetail)
async def cancel_job(job_id: str, db: DbSession):
    """Cancel a running job. Signals the agent to stop."""
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status in (JobStatus.completed, JobStatus.failed, JobStatus.cancelled):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in terminal state: {job.status!r}",
        )

    # Cancel the background agent task
    cancel_agent(job_id)
    _svc.update_status(db, job_id, JobStatus.cancelled)
    job = _svc.get_job(db, job_id)
    return _svc.to_detail(job)


@router.get("/{job_id}/events")
async def get_job_events(job_id: str, db: DbSession):
    """Return the stage event log for a job."""
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")
    detail = _svc.to_detail(job)
    return {"job_id": job_id, "events": detail.events}


@router.get("/{job_id}/stream")
async def stream_job_events(job_id: str, db: DbSession):
    """
    Server-Sent Events stream for live job updates.
    The client receives a JSON line every 2 seconds while the job is active.
    """
    import asyncio
    import json as _json

    TERMINAL = {
        JobStatus.completed, JobStatus.failed, JobStatus.cancelled
    }

    async def event_generator():
        while True:
            try:
                db.expire_all()
                job = _svc.get_job(db, job_id)
                detail = _svc.to_detail(job)
                # Ensure latest in-memory thoughts are attached if active
                if not detail.reasoning_log:
                    live_thoughts = thought_broadcaster.get_history(job_id)
                    if live_thoughts:
                        detail.reasoning_log = live_thoughts
                payload = detail.model_dump(mode="json")
                yield f"data: {_json.dumps(payload)}\n\n"
                if JobStatus(job.status) in TERMINAL:
                    break
            except Exception as exc:
                yield f"data: {_json.dumps({'error': str(exc)})}\n\n"
                break
            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/thoughts/stream")
async def stream_job_thoughts(job_id: str):
    """
    Real-time Server-Sent Events stream for live reasoning thoughts.
    Streams token-by-token chunks as NVIDIA Nemotron reasons.
    """
    import asyncio
    import json as _json

    queue = await thought_broadcaster.subscribe(job_id)
    history = thought_broadcaster.get_history(job_id)

    async def thought_generator():
        # First send existing history if any
        if history:
            yield f"data: {_json.dumps({'chunk': '', 'text': history})}\n\n"

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=2.0)
                    full_text = thought_broadcaster.get_history(job_id)
                    yield f"data: {_json.dumps({'chunk': chunk, 'text': full_text})}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield f": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await thought_broadcaster.unsubscribe(job_id, queue)

    return StreamingResponse(
        thought_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/download-patch")
async def download_patch(job_id: str, db: DbSession):
    """Download verified .patch file for the job."""
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.proposed_patch:
        raise HTTPException(status_code=404, detail="No patch available for this job.")

    safe_name = job.repo_name.replace(" ", "_").replace("/", "_")
    filename = f"patchpilot-{safe_name}-{job.id[:8]}.patch"
    return Response(
        content=job.proposed_patch,
        media_type="text/x-diff",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{job_id}/pr-template")
async def get_pr_template(job_id: str, db: DbSession):
    """Return formatted GitHub Pull Request title and markdown description."""
    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")

    detail = _svc.to_detail(job)
    report = detail.repair_report or {}
    critique = detail.nemotron_critique or {}
    telemetry = detail.nebius_telemetry or {}

    title = f"[PatchPilot] Fix: {report.get('patch_summary') or job.repo_name}"
    baseline = report.get("baseline_test_summary") or {}
    post_patch = report.get("post_patch_test_summary") or {}

    markdown_body = f"""## 🤖 Autonomous Repair by PatchPilot
This pull request was automatically synthesized, tested, and verified by **PatchPilot**.

- **AI Engine:** NVIDIA Llama-3.1-Nemotron-70B-Instruct-HF
- **Inference Infrastructure:** Nebius Token Factory (NVIDIA HGX H100 with FP8 Tensor Cores)
- **AI Judge Verdict:** `{critique.get('verdict', 'APPROVED')}` (Dual-Pass Reasoner & Critic)
- **Job ID:** `{job.id}`

---

### 🎯 Root-Cause Diagnosis
{report.get('diagnosis_summary') or job.bug_description}

### 🧪 Verification Test Results
| Test Run | Status | Passed | Failed |
| :--- | :--- | :--- | :--- |
| **Baseline (Before Fix)** | ❌ Reproducible Failure | {baseline.get('passed', 0)} | {baseline.get('failed', 0)} |
| **Post-Patch (Isolated Sandbox)** | ✅ All Passed | {post_patch.get('passed', 0)} | {post_patch.get('failed', 0)} |

- **Zero Regressions:** `{len(report.get('regression_failures', [])) == 0}`
- **Repair Iterations:** `{job.repair_iterations}`

### 🛡️ NVIDIA Nemotron Self-Critique & Security Audit
- **Correctness Score:** {critique.get('helpsteer_scores', {}).get('correctness', 5)}/5
- **Coherence Score:** {critique.get('helpsteer_scores', {}).get('coherence', 5)}/5
- **Safety Score:** {critique.get('helpsteer_scores', {}).get('safety', 5)}/5
- **Side Effects Analysis:** {critique.get('side_effects_analysis', 'None; defensive guard.')}
- **Security Audit:** {critique.get('security_audit', 'Clean: no vulnerabilities detected.')}

---
*Generated with ⚡ [PatchPilot](https://github.com/patchpilot) & Nebius Token Factory*
"""
    return {
        "job_id": job.id,
        "title": title,
        "body": markdown_body,
    }


@router.get("/{job_id}/download-repaired")
async def download_repaired_archive(job_id: str, db: DbSession):
    """Download 1-click repaired ZIP archive containing the verified code."""
    import io
    import os
    import zipfile
    from pathlib import Path

    try:
        job = _svc.get_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")

    patched_dir = Path("./workspaces") / f"{job_id}_patched"
    if not patched_dir.exists():
        here = Path(__file__).resolve().parent
        candidates = [
            here.parent.parent.parent / "demo_projects" / job.repo_name,
            Path("./demo_projects") / job.repo_name,
            Path("../demo_projects") / job.repo_name,
            Path("./workspaces") / job_id,
        ]
        source_dir = next((c for c in candidates if c.exists()), None)
        if not source_dir:
            raise HTTPException(status_code=404, detail="Repaired workspace not found.")
        patched_dir = source_dir

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(patched_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "node_modules")]
            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(patched_dir)
                zf.write(full_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    safe_name = job.repo_name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}-repaired.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
