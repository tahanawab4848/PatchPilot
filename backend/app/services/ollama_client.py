"""
OllamaClient: local LLM inference provider via Ollama HTTP API.

This is a FALLBACK provider for development when no Nebius API key is available.
It implements the InferenceProvider protocol so it is a drop-in replacement for NemotronClient.

Usage:
  Set OLLAMA_BASE_URL=http://localhost:11434 and INFERENCE_PROVIDER=ollama in .env
  to use a local Ollama model instead of Nebius.

Security:
  - Only connects to localhost by default. Never expose to untrusted networks.
  - Never logs prompt content.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.inference import InferenceMessage, InferenceRequest, InferenceResponse, ModelHealthResponse
from app.services.nebius_client import InferenceError, InferenceUnavailableError

log = get_logger(__name__)

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


class OllamaClient:
    """
    Local Ollama inference client.
    Implements the InferenceProvider protocol.

    Ollama exposes an OpenAI-compatible /v1 endpoint from version 0.1.24+,
    so we use its /api/chat endpoint directly for broader compatibility.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        base_url = getattr(self._settings, "ollama_base_url", _DEFAULT_OLLAMA_URL)
        model = getattr(self._settings, "ollama_model_id", _DEFAULT_OLLAMA_MODEL)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = 120.0

    async def complete(self, request: InferenceRequest) -> InferenceResponse:
        """Send a chat completion request to Ollama /api/chat."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        log.info("ollama_request", model=self._model, message_count=len(messages))

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as exc:
            raise InferenceUnavailableError(
                f"Ollama is not reachable at {self._base_url}. "
                "Start Ollama with: ollama serve"
            ) from exc
        except Exception as exc:
            log.error("ollama_error", error=str(exc))
            raise InferenceError(f"Ollama request failed: {exc}") from exc

        content = data.get("message", {}).get("content", "")
        if not content.strip():
            raise InferenceError("Ollama returned an empty response.")

        prompt_tokens = data.get("prompt_eval_count", 0) or 0
        completion_tokens = data.get("eval_count", 0) or 0

        log.info(
            "ollama_response",
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return InferenceResponse(
            content=content,
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=data.get("done_reason", "stop"),
        )

    async def complete_json(self, request: InferenceRequest) -> Dict[str, Any]:
        """Like complete(), but parses the response as JSON."""
        response = await self.complete(request)
        # Try to extract JSON from the response content
        content = response.content.strip()
        # Find JSON block if wrapped in markdown
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise InferenceError(
                f"Ollama returned non-JSON response: {content[:200]!r}"
            ) from exc

    async def health_check(self) -> ModelHealthResponse:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_available = any(self._model in m for m in models)
                if not model_available and models:
                    return ModelHealthResponse(
                        configured=True,
                        model_id=self._model,
                        base_url=self._base_url,
                        reachable=True,
                        error=f"Model {self._model!r} not pulled. Available: {models[:5]}. Run: ollama pull {self._model}",
                    )
                return ModelHealthResponse(
                    configured=True,
                    model_id=self._model,
                    base_url=self._base_url,
                    reachable=True,
                )
        except httpx.ConnectError:
            return ModelHealthResponse(
                configured=False,
                model_id=self._model,
                base_url=self._base_url,
                reachable=False,
                error=f"Ollama not reachable at {self._base_url}. Run: ollama serve",
            )
        except Exception as exc:
            return ModelHealthResponse(
                configured=False,
                model_id=self._model,
                base_url=self._base_url,
                reachable=False,
                error=str(exc),
            )
