"""
Live inference verification test for NVIDIA Nemotron via Nebius Token Factory.

Only runs when valid Nebius credentials are configured.
Otherwise skips gracefully.
"""

from __future__ import annotations

import os
import pytest

from app.core.config import get_settings
from app.schemas.inference import InferenceMessage, InferenceRequest
from app.services.nebius_client import NemotronClient


@pytest.mark.asyncio
async def test_live_nebius_inference():
    """
    Verifies a real inference call against Nebius Token Factory
    when NEBIUS_API_KEY is configured in the environment.
    """
    settings = get_settings()
    if not settings.nebius_configured:
        pytest.skip(
            "NEBIUS_API_KEY is not configured or is a placeholder. "
            "Set a valid NEBIUS_API_KEY in .env to run live provider tests."
        )

    client = NemotronClient(settings)
    health = await client.health_check()
    assert health.configured is True
    assert health.reachable is True
    assert health.error is None

    req = InferenceRequest(
        messages=[
            InferenceMessage(role="system", content="You are a test assistant. Reply strictly with the requested word."),
            InferenceMessage(role="user", content="Reply with the exact word: PONG"),
        ],
        temperature=0.0,
        max_tokens=10,
    )
    res = await client.complete(req)
    assert res.content is not None
    assert len(res.content.strip()) > 0
    assert res.finish_reason in ("stop", "length")
