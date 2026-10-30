"""
ToolRegistry: Approved diagnostics and investigation tools for the DebuggingAgent.

Security guarantees:
- No unrestricted shell access.
- Explicit allow-list of tools.
- Strict path validation against repo root (preventing path traversal).
- Hard budget limits on total calls and output size to prevent infinite loops and token explosions.
- Every invocation is audited and logged.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.logging import get_logger
from app.sandbox.executor import ExecutionService
from app.schemas.execution import ExecutionResult
from app.services.repository_service import RepositoryService
from app.services.test_runner import TestRunner

log = get_logger(__name__)


class ToolBudgetExceeded(Exception):
    pass


class ToolExecutionError(Exception):
    pass


class ToolRegistry:
    """
    Approved tool registry for bounded agent investigation (Stage D).
    """

    def __init__(
        self,
        repo_root: Path,
        repo_svc: RepositoryService,
        exec_svc: ExecutionService,
        test_runner: TestRunner,
        max_tool_calls: int = 20,
    ) -> None:
        self.repo_root = repo_root
        self._repo_svc = repo_svc
        self._exec_svc = exec_svc
        self._test_runner = test_runner
        self.max_tool_calls = max_tool_calls
        self.call_count = 0
        self.history: List[Dict[str, Any]] = []
        self._command_results: Dict[str, ExecutionResult] = {}

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return specifications of all registered tools."""
        return [
            {
                "name": "list_files",
                "description": "List files in the repository under an optional subfolder.",
                "parameters": {
                    "subfolder": {"type": "string", "description": "Relative folder path (optional)"},
                    "max_entries": {"type": "integer", "description": "Max entries to return (default 50)"},
                },
            },
            {
                "name": "read_file_excerpt",
                "description": "Read bounded source-file lines with line numbers.",
                "parameters": {
                    "file_path": {"type": "string", "description": "Relative file path"},
                    "start_line": {"type": "integer", "description": "1-based starting line number"},
                    "max_lines": {"type": "integer", "description": "Max lines to return (capped at 150)"},
                },
            },
            {
                "name": "search_source",
                "description": "Search source code for a text snippet or identifier.",
                "parameters": {
                    "query": {"type": "string", "description": "Text or symbol to search for"},
                    "max_matches": {"type": "integer", "description": "Max matching lines (capped at 20)"},
                },
            },
            {
                "name": "inspect_manifest",
                "description": "Inspect a supported manifest (requirements.txt, pyproject.toml, package.json).",
                "parameters": {
                    "manifest_path": {"type": "string", "description": "Relative path to the manifest file"},
                },
            },
            {
                "name": "run_approved_test_command",
                "description": "Run pytest with an optional test file filter in the isolated sandbox.",
                "parameters": {
                    "test_path": {"type": "string", "description": "Optional test file or node id to execute"},
                },
            },
            {
                "name": "get_command_result",
                "description": "Retrieve stdout, stderr, and exit code from a previously executed command.",
                "parameters": {
                    "command_id": {"type": "string", "description": "Command identifier"},
                },
            },
        ]

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate, authorize, execute, and record an approved tool call.
        """
        if self.call_count >= self.max_tool_calls:
            raise ToolBudgetExceeded(
                f"Tool call budget exhausted ({self.call_count}/{self.max_tool_calls} calls)."
            )

        self.call_count += 1
        log.info("tool_call_start", tool=tool_name, call_index=self.call_count)

        tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "list_files": self._tool_list_files,
            "read_file_excerpt": self._tool_read_file_excerpt,
            "search_source": self._tool_search_source,
            "inspect_manifest": self._tool_inspect_manifest,
            "run_approved_test_command": self._tool_run_approved_test_command,
            "get_command_result": self._tool_get_command_result,
        }

        handler = tools.get(tool_name)
        if not handler:
            res = {"error": f"Unknown tool: {tool_name!r}. Allowed: {list(tools.keys())}"}
        else:
            try:
                res = handler(arguments)
            except Exception as exc:
                log.warning("tool_call_error", tool=tool_name, error=str(exc))
                res = {"error": f"Tool execution failed: {exc}"}

        record = {
            "index": self.call_count,
            "tool": tool_name,
            "arguments": arguments,
            "result": res,
        }
        self.history.append(record)
        return res

    # ── Tool Implementations ────────────────────────────────────────────────────

    def _tool_list_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        subfolder = str(args.get("subfolder", "") or "").strip().lstrip("/\\")
        max_entries = min(int(args.get("max_entries", 50) or 50), 100)
        target_dir = (self.repo_root / subfolder).resolve()

        if not str(target_dir).startswith(str(self.repo_root.resolve())):
            return {"error": f"Path traversal rejected: {subfolder!r}"}
        if not target_dir.exists() or not target_dir.is_dir():
            return {"error": f"Directory not found: {subfolder!r}"}

        entries = []
        for p in self._repo_svc._walk(target_dir):
            rel = str(p.relative_to(self.repo_root)).replace("\\", "/")
            entries.append(rel)
            if len(entries) >= max_entries:
                break
        return {"files": entries, "count": len(entries)}

    def _tool_read_file_excerpt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = str(args.get("file_path", "")).strip()
        start_line = max(1, int(args.get("start_line", 1) or 1))
        max_lines = min(max(1, int(args.get("max_lines", 100) or 100)), 150)

        try:
            content, total = self._repo_svc.read_file_excerpt(
                self.repo_root, file_path, start_line=start_line, max_lines=max_lines
            )
            return {
                "file_path": file_path,
                "start_line": start_line,
                "end_line": min(total, start_line + max_lines - 1),
                "total_lines": total,
                "content": content[:8000],
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _tool_search_source(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"error": "Query cannot be empty"}
        max_matches = min(max(1, int(args.get("max_matches", 20) or 20)), 50)

        matches = []
        for file_path in self._repo_svc._walk(self.repo_root):
            if file_path.suffix.lower() not in (".py", ".js", ".ts", ".json", ".md", ".txt"):
                continue
            rel_str = str(file_path.relative_to(self.repo_root)).replace("\\", "/")
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
                for line_no, line in enumerate(lines, start=1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": rel_str,
                            "line": line_no,
                            "snippet": line.strip()[:150],
                        })
                        if len(matches) >= max_matches:
                            break
            except Exception:
                continue
            if len(matches) >= max_matches:
                break
        return {"query": query, "matches": matches, "count": len(matches)}

    def _tool_inspect_manifest(self, args: Dict[str, Any]) -> Dict[str, Any]:
        manifest_path = str(args.get("manifest_path", "")).strip()
        safe_path = self.repo_root / manifest_path.lstrip("/\\")
        if not str(safe_path.resolve()).startswith(str(self.repo_root.resolve())):
            return {"error": "Path traversal rejected"}
        if not safe_path.exists():
            return {"error": f"Manifest not found: {manifest_path}"}
        try:
            content = safe_path.read_text(encoding="utf-8", errors="replace")[:6000]
            return {"manifest_path": manifest_path, "content": content}
        except Exception as exc:
            return {"error": str(exc)}

    def _tool_run_approved_test_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        test_path = args.get("test_path")
        paths = [str(test_path).strip()] if test_path else None
        cmd = self._test_runner.build_pytest_command(test_paths=paths)

        cmd_id = f"cmd_{len(self._command_results) + 1}"
        exec_result = self._exec_svc.run_command(cmd, self.repo_root)
        self._command_results[cmd_id] = exec_result

        return {
            "command_id": cmd_id,
            "command": " ".join(cmd),
            "status": exec_result.status.value,
            "exit_code": exec_result.exit_code,
            "duration_seconds": exec_result.duration_seconds,
            "stdout_tail": exec_result.stdout[-1500:] if exec_result.stdout else "",
            "stderr_tail": exec_result.stderr[-1000:] if exec_result.stderr else "",
        }

    def _tool_get_command_result(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd_id = str(args.get("command_id", "")).strip()
        if cmd_id not in self._command_results:
            return {"error": f"Command ID {cmd_id!r} not found. Available: {list(self._command_results.keys())}"}
        res = self._command_results[cmd_id]
        return {
            "command_id": cmd_id,
            "command": " ".join(res.command),
            "status": res.status.value,
            "exit_code": res.exit_code,
            "stdout": res.stdout[:4000],
            "stderr": res.stderr[:2000],
        }
