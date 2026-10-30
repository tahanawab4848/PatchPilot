"""
Job and JobEvent ORM models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Repository information
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_source: Mapped[str] = mapped_column(String(32), nullable=False)  # "upload" | "demo"
    # Relative path inside upload storage where the archive is kept
    archive_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Bug report submitted by the user
    bug_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Current lifecycle state
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")

    # Detected project metadata (JSON blob)
    project_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generated patch (unified diff, stored as text)
    proposed_patch: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NVIDIA Nemotron Dual-Pass Reasoner & Critic (JSON blob)
    nemotron_critique: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nebius Token Factory live telemetry (JSON blob)
    nebius_telemetry: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Live streaming reasoning log from NVIDIA Nemotron
    reasoning_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Approval state: None | "approved" | "rejected" | "revised" | "cancelled"
    patch_approval: Mapped[str | None] = mapped_column(String(16), nullable=True)
    patch_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Final repair report (JSON blob)
    repair_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error detail when status == "failed"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Number of repair iterations attempted
    repair_iterations: Mapped[int] = mapped_column(Integer, default=0)

    events: Mapped[list[JobEvent]] = relationship(
        "JobEvent", back_populates="job", cascade="all, delete-orphan", order_by="JobEvent.created_at"
    )


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "started" | "completed" | "failed"
    # Structured event details as JSON
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship("Job", back_populates="events")
