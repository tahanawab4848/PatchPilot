import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

SECRET_KEY = "patchpilot-insecure-test-secret-key-change-in-prod"


class AuthenticationError(Exception):
    pass


class TokenExpiredError(AuthenticationError):
    pass


class TokenInvalidError(AuthenticationError):
    pass


def create_access_token(username: str, role: str = "member", expires_delta: int = 3600) -> str:
    """Create a signed HMAC-SHA256 token with expiration timestamp."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_delta,
    }
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify the signature and expiration timestamp of the given token.
    Raises TokenExpiredError or TokenInvalidError on failure.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenInvalidError("Malformed token structure")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise TokenInvalidError("Invalid signature")

    # Decode payload
    padding = "=" * ((4 - len(payload_b64) % 4) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
    payload = json.loads(payload_bytes.decode())

    # DEFECT: The comparison operator is inverted (> instead of <)
    # Tokens whose expiration is in the future are erroneously treated as expired!
    if payload.get("exp") is not None and payload["exp"] > time.time():
        raise TokenExpiredError("Token has expired")

    return payload
