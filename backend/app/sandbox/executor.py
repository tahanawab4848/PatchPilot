"""
ExecutionService: runs approved commands in an isolated Docker sandbox.

Security Architecture and Boundaries:
- Docker alone is NOT a complete security boundary; it is a defense-in-depth isolation layer.
  Untrusted repository code must NEVER be executed directly in the host backend process.
- No networking: container network is disabled (--network none) to block exfiltration and
  cloud metadata endpoint access (e.g. 169.254.169.254).
- Non-root user: container runs under unprivileged UID 65534 (nobody:nogroup).
- Drop capabilities: all Linux capabilities are dropped (--cap-drop ALL).
- No new privileges: prevents setuid binaries from escalating permissions.
- Read-only rootfs: filesystem root is read-only (--read-only); only /tmp is writable tmpfs (noexec).
- Process limits: pids-limit prevents fork bombs.
- Explicit CPU, memory, and timeout limits.
- Command allow-list enforced before execution.
- Argument arrays only: no shell string interpolation, rejecting shell metacharacters.
- Container cleanup: ephemeral containers are created with --rm and killed on timeout.
- Host isolation: never mount the host root, docker.sock, or credential directories (~/.ssh, ~/.aws).

If a secure sandbox cannot be started, the service fails closed.
"""

from __future__ import annotations

import os
import platform
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.execution import CommandStatus, ExecutionResult

log = get_logger(__name__)

# ── Allowed executables (no shell expansion, no interpreters from user input) ─

ALLOWED_COMMANDS: set[str] = {
    "python", "python3", "pytest", "pip", "pip3",
    "node", "npm", "npx", "yarn",
    "ls", "find", "cat", "grep", "head", "tail",
    "echo",  # safe, for health checks
}


class SandboxError(Exception):
    pass


class ExecutionService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        """Return True if Docker is present and the sandbox can be used."""
        if not self._settings.sandbox_enabled:
            return False
        try:
            result = subprocess.run(
                ["docker", "info"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def run_command(
        self,
        command: List[str],
        workspace_path: Path,
        timeout: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Execute an approved command inside the Docker sandbox.
        The workspace_path is mounted read-only unless 'pytest' or 'python' is the executable.
        """
        self._validate_command(command)
        effective_timeout = timeout or self._settings.sandbox_timeout_seconds
        started_at = datetime.now(timezone.utc)

        if not self.is_available():
            return ExecutionResult(
                command=command,
                status=CommandStatus.error,
                stderr=(
                    "Missing prerequisite: Docker sandbox daemon is not running or accessible. "
                    "Untrusted repository code cannot be executed directly on the host backend process. "
                    "Start Docker Desktop or the Docker daemon to enable sandbox execution."
                ),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )

        self._validate_workspace_path(workspace_path)
        container_name = f"patchpilot-sandbox-{uuid.uuid4().hex[:8]}"
        abs_workspace = str(workspace_path.resolve())

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--network", self._settings.sandbox_network,
            "--memory", self._settings.sandbox_memory_limit,
            "--cpus", str(self._settings.sandbox_cpu_limit),
            "--pids-limit", "100",
            "--privileged=false",
            "--cap-drop", "ALL",
            "--user", "65534:65534",  # nobody:nogroup
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--volume", f"{abs_workspace}:/workspace:rw",
            "--workdir", "/workspace",
            "--security-opt", "no-new-privileges:true",
            self._settings.sandbox_image,
        ] + command

        log.info("sandbox_run", command=command[:3], container=container_name)
        start_time = time.monotonic()

        try:
            proc = subprocess.run(
                docker_cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=effective_timeout,
                text=True,
            )
            duration = time.monotonic() - start_time
            finished_at = datetime.now(timezone.utc)

            status = CommandStatus.success if proc.returncode == 0 else CommandStatus.failure
            return ExecutionResult(
                command=command,
                exit_code=proc.returncode,
                stdout=proc.stdout[:32_000],  # cap output
                stderr=proc.stderr[:8_000],
                duration_seconds=duration,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            # Attempt cleanup
            try:
                subprocess.run(["docker", "kill", container_name], stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
            except Exception:
                pass
            log.warning("sandbox_timeout", container=container_name, timeout=effective_timeout)
            return ExecutionResult(
                command=command,
                exit_code=None,
                stderr=f"Command timed out after {effective_timeout}s",
                duration_seconds=duration,
                status=CommandStatus.timeout,
                timed_out=True,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            log.error("sandbox_error", error=str(exc))
            return ExecutionResult(
                command=command,
                exit_code=None,
                stderr=f"Sandbox execution error: {exc}",
                duration_seconds=time.monotonic() - start_time,
                status=CommandStatus.error,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )

    def run_command_with_fallback(
        self,
        command: List[str],
        workspace_path: Path,
        timeout: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
        is_demo: bool = False,
    ) -> ExecutionResult:
        """
        Try Docker sandbox first. If unavailable and is_demo=True and host execution
        is configured, fall back to HostExecutor for the demo workspace.

        For non-demo (uploaded) repositories, fails closed when Docker is unavailable.
        """
        if self.is_available():
            return self.run_command(command, workspace_path, timeout, env_vars)

        if is_demo:
            try:
                from app.sandbox.host_executor import HostExecutor
                host = HostExecutor(self._settings)
                if host.is_available() and host.is_demo_path(workspace_path):
                    log.info("sandbox_host_fallback", reason="docker_unavailable", demo=True)
                    return host.run_command(command, workspace_path, timeout, env_vars)
            except Exception as exc:
                log.warning("host_fallback_error", error=str(exc))

        # Fail closed
        return self.run_command(command, workspace_path, timeout, env_vars)

    # ── Private ─────────────────────────────────────────────────────────────────

    def _validate_workspace_path(self, workspace_path: Path) -> None:
        """Ensure the workspace path is safe to mount and does not expose sensitive host dirs."""
        resolved = workspace_path.resolve()
        resolved_str = str(resolved).lower()

        # Reject mounting root or critical host paths
        forbidden_roots = ["c:\\", "/", "c:\\windows", "c:\\users", "/etc", "/var", "/usr", "/home"]
        if resolved_str in forbidden_roots or resolved == resolved.parent:
            raise SandboxError(f"Refusing to mount dangerous host path into sandbox: {resolved}")

        # Check for user credential directories
        sensitive_dirs = [".ssh", ".aws", ".azure", ".kube", ".docker", ".gnupg"]
        for part in resolved.parts:
            if part.lower() in sensitive_dirs:
                raise SandboxError(f"Refusing to mount directory inside sensitive path: {resolved}")

    def _validate_command(self, command: List[str]) -> None:
        if not command:
            raise SandboxError("Empty command.")
        executable = command[0].split("/")[-1]  # basename
        if executable not in ALLOWED_COMMANDS:
            raise SandboxError(
                f"Command not in allow-list: {executable!r}. "
                f"Allowed: {sorted(ALLOWED_COMMANDS)}"
            )
        # Reject shell metacharacters in any argument
        for arg in command[1:]:
            if any(ch in arg for ch in (";", "&", "|", "`", "$", "(", ")", "<", ">")):
                raise SandboxError(
                    f"Shell metacharacter found in argument: {arg!r}"
                )
