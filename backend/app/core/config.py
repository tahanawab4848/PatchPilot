"""
Application configuration loaded from environment variables.
All secrets are server-side only; nothing here is exposed to the browser.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "PatchPilot"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Server ─────────────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    allowed_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./patchpilot.db"

    # ── Nebius / NVIDIA Inference ──────────────────────────────────────────────
    nebius_api_base_url: str = "https://api.studio.nebius.ai/v1"
    nebius_api_key: str = ""
    nebius_model_id: str = "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"
    nebius_request_timeout: int = 120
    nebius_max_retries: int = 3

    # ── Upload limits ──────────────────────────────────────────────────────────
    max_upload_size_mb: int = 50
    max_repo_files: int = 2000
    max_file_size_kb: int = 512

    # ── Sandbox ────────────────────────────────────────────────────────────────
    sandbox_enabled: bool = True
    sandbox_timeout_seconds: int = 120
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: float = 1.0
    sandbox_network: str = "none"
    sandbox_image: str = "python:3.11-slim"

    # ── Agent ──────────────────────────────────────────────────────────────────
    agent_max_repair_iterations: int = 3
    agent_max_tool_calls: int = 20
    agent_max_context_tokens: int = 8000

    # ── Inference Provider ──────────────────────────────────────────────────────
    inference_provider: str = "nebius"  # "nebius" or "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_id: str = "llama3.1:8b"

    # ── Demo Sandbox (host execution, trusted demo projects only) ───────────────
    sandbox_allow_host_execution_for_demo: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    @property
    def nebius_configured(self) -> bool:
        """True when a real API key is present (not placeholder)."""
        key = self.nebius_api_key.strip()
        return bool(key) and key != "your_nebius_api_key_here"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_size_kb * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
