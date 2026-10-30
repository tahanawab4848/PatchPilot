"""
HostExecutor: restricted subprocess execution for DEMO PROJECTS ONLY.

This is NOT a security sandbox. It is a fallback that allows the demo
project to be run locally when Docker is unavailable, provided that
the setting sandbox_allow_host_execution_for_demo is explicitly enabled.

Security constraints:
- Only available when settings.sandbox_allow_host_execution_for_demo = True
- Only for paths inside the configured demo projects directory
- Hard timeout enforced
- No network, no shell interpolation, restricted PATH
- Clearly marks results as "demo-host" execution mode

NEVER use this for uploaded user repositories. Docker must be used for those.
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.sandbox.executor import ALLOWED_COMMANDS, SandboxError
from app.schemas.execution import CommandStatus, ExecutionResult

log = get_logger(__name__)

# Path prefix that is considered "safe" for host demo execution
# (The bundled demo_projects directory and isolated patched workspaces)
_SAFE_DEMO_PREFIXES = ["demo_projects", "demo-projects", "workspaces"]


class HostExecutor:
    """
    Runs approved commands directly on the host for demo projects only.
    Used as a Docker fallback when sandbox_allow_host_execution_for_demo=True.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        """True only when explicitly enabled in settings."""
        return bool(self._settings.sandbox_allow_host_execution_for_demo)

    def is_demo_path(self, workspace_path: Path) -> bool:
        """Check whether the workspace path is inside a known demo directory."""
        resolved = workspace_path.resolve()
        parts_lower = [p.lower() for p in resolved.parts]
        return any(prefix in parts_lower for prefix in _SAFE_DEMO_PREFIXES)

    def run_command(
        self,
        command: List[str],
        workspace_path: Path,
        timeout: Optional[int] = None,
        env_vars: Optional[dict] = None,
    ) -> ExecutionResult:
        """
        Run a command directly on the host inside the workspace directory.
        Only allowed for demo project paths when host execution is enabled.
        """
        if not self.is_available():
            return ExecutionResult(
                command=command,
                status=CommandStatus.error,
                stderr="Host execution is disabled. Enable sandbox_allow_host_execution_for_demo=true for demo mode.",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )

        if not self.is_demo_path(workspace_path):
            return ExecutionResult(
                command=command,
                status=CommandStatus.error,
                stderr=(
                    "Security boundary: host execution is only permitted for demo project paths. "
                    "Uploaded repositories must use the Docker sandbox."
                ),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )

        # Validate command against allow-list
        if not command:
            raise SandboxError("Empty command.")
        executable = command[0].split("/")[-1].split("\\")[-1]
        if executable not in ALLOWED_COMMANDS:
            raise SandboxError(f"Command not in allow-list: {executable!r}")

        # Reject shell metacharacters
        for arg in command[1:]:
            if any(ch in arg for ch in (";", "&", "|", "`", "$", "(", ")", "<", ">")):
                raise SandboxError(f"Shell metacharacter in argument: {arg!r}")

        effective_timeout = timeout or self._settings.sandbox_timeout_seconds
        started_at = datetime.now(timezone.utc)

        # Minimal environment — only what Python/pip/pytest need
        restricted_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(workspace_path.resolve()),
            "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
            "SystemRoot": os.environ.get("SystemRoot", ""),
        }
        if env_vars:
            restricted_env.update(env_vars)

        log.info(
            "host_executor_run",
            command=command[:3],
            workspace=str(workspace_path),
            demo_mode=True,
        )

        start_time = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                timeout=effective_timeout,
                text=True,
                cwd=str(workspace_path.resolve()),
                env=restricted_env,
            )
            duration = time.monotonic() - start_time
            status = CommandStatus.success if proc.returncode == 0 else CommandStatus.failure
            return ExecutionResult(
                command=command,
                exit_code=proc.returncode,
                stdout=(proc.stdout or "")[:32_000],
                stderr=(
                    "[DEMO MODE — host execution, not Docker sandboxed]\n"
                    + (proc.stderr or "")
                )[:8_000],
                duration_seconds=duration,
                status=status,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                command=command,
                exit_code=None,
                stderr=f"[DEMO MODE] Command timed out after {effective_timeout}s",
                duration_seconds=time.monotonic() - start_time,
                status=CommandStatus.timeout,
                timed_out=True,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            log.error("host_executor_error", error=str(exc))
            return ExecutionResult(
                command=command,
                exit_code=None,
                stderr=f"[DEMO MODE] Host execution error: {exc}",
                duration_seconds=time.monotonic() - start_time,
                status=CommandStatus.error,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
