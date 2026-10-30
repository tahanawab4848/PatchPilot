"""
JobService: manages persistent job lifecycle and event recording.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import Job, JobEvent
from app.schemas.job import CreateJobRequest, JobDetail, JobEventSchema, JobStatus, JobSummary

log = get_logger(__name__)


class JobNotFoundError(Exception):
    pass


class JobService:
    def create_job(self, db: Session, request: CreateJobRequest) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            repo_name=request.repo_name,
            repo_source=request.repo_source,
            archive_path=request.archive_path,
            bug_description=request.bug_description,
            status=JobStatus.queued,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        log.info("job_created", job_id=job.id, repo=job.repo_name)
        return job

    def get_job(self, db: Session, job_id: str) -> Job:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise JobNotFoundError(f"Job {job_id!r} not found.")
        return job

    def list_jobs(self, db: Session, limit: int = 50, offset: int = 0) -> List[Job]:
        return (
            db.query(Job)
            .order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        db: Session,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> Job:
        job = self.get_job(db, job_id)
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        if error_message:
            job.error_message = error_message
        db.commit()
        db.refresh(job)
        log.info("job_status_updated", job_id=job_id, status=status)
        return job

    def set_project_metadata(
        self, db: Session, job_id: str, metadata: Dict[str, Any]
    ) -> None:
        job = self.get_job(db, job_id)
        job.project_metadata = json.dumps(metadata)
        db.commit()

    def set_proposed_patch(
        self, db: Session, job_id: str, patch_diff: str
    ) -> None:
        job = self.get_job(db, job_id)
        job.proposed_patch = patch_diff
        job.status = JobStatus.awaiting_approval
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def set_nemotron_critique(
        self, db: Session, job_id: str, critique: Dict[str, Any]
    ) -> None:
        job = self.get_job(db, job_id)
        job.nemotron_critique = json.dumps(critique)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def set_nebius_telemetry(
        self, db: Session, job_id: str, telemetry: Dict[str, Any]
    ) -> None:
        job = self.get_job(db, job_id)
        job.nebius_telemetry = json.dumps(telemetry)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def set_reasoning_log(
        self, db: Session, job_id: str, reasoning_text: str
    ) -> None:
        job = self.get_job(db, job_id)
        job.reasoning_log = reasoning_text
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def set_patch_approval(
        self, db: Session, job_id: str, decision: str, feedback: Optional[str] = None
    ) -> None:
        job = self.get_job(db, job_id)
        job.patch_approval = decision
        if feedback is not None:
            job.patch_feedback = feedback
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def set_repair_report(
        self, db: Session, job_id: str, report: Dict[str, Any]
    ) -> None:
        job = self.get_job(db, job_id)
        job.repair_report = json.dumps(report)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    def increment_repair_iterations(self, db: Session, job_id: str) -> None:
        job = self.get_job(db, job_id)
        job.repair_iterations = (job.repair_iterations or 0) + 1
        db.commit()

    def add_event(
        self,
        db: Session,
        job_id: str,
        stage: str,
        status: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JobEvent:
        event = JobEvent(
            id=str(uuid.uuid4()),
            job_id=job_id,
            stage=stage,
            status=status,
            message=message,
            details=json.dumps(details) if details else None,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        log.debug("job_event", job_id=job_id, stage=stage, status=status)
        return event

    def to_detail(self, job: Job) -> JobDetail:
        events = []
        for e in job.events:
            details_parsed: Optional[Dict[str, Any]] = None
            if e.details:
                try:
                    details_parsed = json.loads(e.details)
                except json.JSONDecodeError:
                    pass
            events.append(JobEventSchema(
                id=e.id,
                job_id=e.job_id,
                created_at=e.created_at,
                stage=e.stage,
                status=e.status,
                details=details_parsed,
                message=e.message,
            ))

        metadata_parsed = None
        if job.project_metadata:
            try:
                metadata_parsed = json.loads(job.project_metadata)
            except json.JSONDecodeError:
                pass

        report_parsed = None
        if job.repair_report:
            try:
                report_parsed = json.loads(job.repair_report)
            except json.JSONDecodeError:
                pass

        critique_parsed = None
        if getattr(job, "nemotron_critique", None):
            try:
                critique_parsed = json.loads(job.nemotron_critique)
            except json.JSONDecodeError:
                pass

        telemetry_parsed = None
        if getattr(job, "nebius_telemetry", None):
            try:
                telemetry_parsed = json.loads(job.nebius_telemetry)
            except json.JSONDecodeError:
                pass

        return JobDetail(
            id=job.id,
            created_at=job.created_at,
            updated_at=job.updated_at,
            repo_name=job.repo_name,
            repo_source=job.repo_source,
            bug_description=job.bug_description,
            status=job.status,
            project_metadata=metadata_parsed,
            proposed_patch=job.proposed_patch,
            nemotron_critique=critique_parsed,
            nebius_telemetry=telemetry_parsed,
            reasoning_log=getattr(job, "reasoning_log", None),
            patch_approval=job.patch_approval,
            patch_feedback=getattr(job, "patch_feedback", None),
            repair_report=report_parsed,
            error_message=job.error_message,
            repair_iterations=job.repair_iterations or 0,
            events=events,
        )
