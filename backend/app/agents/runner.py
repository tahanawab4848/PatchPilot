"""
AgentRunner: launches DebuggingAgent as an asyncio background task.

A global task registry tracks running agents so they can be cancelled
when a job is cancelled. Tasks are fire-and-forget from the HTTP handler.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from app.core.logging import get_logger

log = get_logger(__name__)

# Registry: job_id → asyncio.Task
_running_tasks: Dict[str, asyncio.Task] = {}


async def launch_agent(job_id: str) -> None:
    """
    Start the DebuggingAgent for job_id as an asyncio background task.
    Import is deferred to avoid circular imports at module load time.
    """
    from app.agents.debugging_agent import DebuggingAgent

    if job_id in _running_tasks:
        t = _running_tasks[job_id]
        if not t.done():
            log.warning("agent_already_running", job_id=job_id)
            return

    agent = DebuggingAgent(job_id=job_id)
    task = asyncio.create_task(agent.run(), name=f"agent-{job_id}")
    _running_tasks[job_id] = task

    def _on_done(t: asyncio.Task) -> None:
        _running_tasks.pop(job_id, None)
        if t.cancelled():
            log.info("agent_task_cancelled", job_id=job_id)
        elif t.exception():
            log.error("agent_task_exception", job_id=job_id, error=str(t.exception()))
        else:
            log.info("agent_task_complete", job_id=job_id)

    task.add_done_callback(_on_done)
    log.info("agent_task_launched", job_id=job_id)


def cancel_agent(job_id: str) -> bool:
    """Cancel a running agent task. Returns True if a task was found."""
    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def get_running_jobs() -> list[str]:
    """Return job_ids of currently running agent tasks."""
    return [jid for jid, t in _running_tasks.items() if not t.done()]
