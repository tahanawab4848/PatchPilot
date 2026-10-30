import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import (
    AuthenticationError,
    TokenExpiredError,
    create_access_token,
    verify_access_token,
)
from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "fastapi_auth_service"}


@pytest.mark.asyncio
async def test_valid_token_allows_access():
    """A fresh, valid token with positive expiration must be accepted."""
    token = create_access_token(username="alice", expires_delta=3600)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_expired_token_rejected():
    """A token whose expiration timestamp is in the past must be rejected."""
    # Token expired 100 seconds ago
    expired_token = create_access_token(username="bob", expires_delta=-100)
    with pytest.raises(TokenExpiredError):
        verify_access_token(expired_token)


@pytest.mark.asyncio
async def test_invalid_signature_rejected():
    """Tampered token signature must raise AuthenticationError."""
    token = create_access_token(username="eve", expires_delta=3600)
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.tamperedsignature"
    with pytest.raises(AuthenticationError):
        verify_access_token(tampered)
