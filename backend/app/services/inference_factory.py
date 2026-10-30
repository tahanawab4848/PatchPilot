"""
inference_factory: returns the configured InferenceProvider implementation.

Usage:
    from app.services.inference_factory import get_inference_client
    client = get_inference_client()  # uses settings.inference_provider

Supported providers:
    "nebius"  → NemotronClient (NVIDIA Nemotron-70B via Nebius, default)
    "ollama"  → OllamaClient  (local model via Ollama, development fallback)
"""

from __future__ import annotations

from typing import Union

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


def get_inference_client(
    settings: Settings | None = None,
) -> Union["NemotronClient", "OllamaClient"]:  # type: ignore[name-defined]
    """
    Return the inference client configured by settings.inference_provider.

    Imports are deferred to avoid circular imports and to keep optional
    dependencies from blocking startup.
    """
    cfg = settings or get_settings()
    provider = (cfg.inference_provider or "nebius").lower().strip()

    if provider == "ollama":
        from app.services.ollama_client import OllamaClient
        log.info("inference_provider", provider="ollama", model=cfg.ollama_model_id)
        return OllamaClient(settings=cfg)

    # Default: nebius / nemotron
    from app.services.nebius_client import NemotronClient
    log.info("inference_provider", provider="nebius", model=cfg.nebius_model_id)
    return NemotronClient(settings=cfg)
