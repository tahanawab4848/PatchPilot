"""
InferenceProvider: Protocol interface for LLM inference providers.

Implementing this protocol allows swapping between:
- NemotronClient (Nebius/NVIDIA — primary)
- OllamaClient (local LLM — fallback for development)
- MockInferenceClient (testing)

All providers must implement complete() and health_check().
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from app.schemas.inference import InferenceRequest, InferenceResponse, ModelHealthResponse


@runtime_checkable
class InferenceProvider(Protocol):
    """Structural protocol for LLM inference providers."""

    async def complete(self, request: InferenceRequest) -> InferenceResponse:
        """Send a completion request and return a validated response."""
        ...

    async def complete_json(self, request: InferenceRequest) -> Dict[str, Any]:
        """Like complete(), but parses and returns the response as JSON dict."""
        ...

    async def health_check(self) -> ModelHealthResponse:
        """Return provider health and configuration status."""
        ...
