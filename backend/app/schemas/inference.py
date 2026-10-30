"""
Nebius / NVIDIA inference request and response schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InferenceMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class InferenceRequest(BaseModel):
    messages: List[InferenceMessage]
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=64, le=32768)
    response_format: Optional[Dict[str, str]] = None  # e.g. {"type": "json_object"}


class InferenceResponse(BaseModel):
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_per_second: float = 0.0
    time_to_first_token_ms: float = 0.0
    system_fingerprint: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None


class ModelHealthResponse(BaseModel):
    configured: bool
    model_id: str
    base_url: str
    reachable: bool
    error: Optional[str] = None
