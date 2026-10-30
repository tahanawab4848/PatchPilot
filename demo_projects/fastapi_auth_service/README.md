# FastAPI Asynchronous Auth Service

Production-ready FastAPI asynchronous authentication microservice using Pydantic V2 schemas and HMAC-SHA256 JWT validation.

## Known Defect
In `src/auth.py`, the token expiration validation in `verify_access_token` checks:
```python
if payload.get("exp") is not None and payload["exp"] > time.time():
    raise TokenExpiredError("Token has expired")
```
The comparison operator is inverted (`>` instead of `<`). As a result:
- Fresh, unexpired active tokens are rejected with HTTP 401 `{"detail": "Token has expired"}`.
- Expired tokens pass verification without triggering expiration.

Failing tests:
- `tests/test_auth_service.py::test_valid_token_allows_access`
- `tests/test_auth_service.py::test_expired_token_rejected`
