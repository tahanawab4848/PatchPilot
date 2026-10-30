from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth import (
    AuthenticationError,
    TokenExpiredError,
    create_access_token,
    verify_access_token,
)
from src.models import TokenResponse, UserCredentials, UserProfile

app = FastAPI(title="FastAPI Auth Service")
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserProfile(username=payload["sub"], role=payload.get("role", "member"))


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserCredentials):
    # Simulated authentication
    if credentials.username and credentials.password == "securepass123":
        token = create_access_token(credentials.username, role="engineer")
        return TokenResponse(access_token=token)
    raise HTTPException(status_code=400, detail="Invalid username or password")


@app.get("/api/v1/users/me", response_model=UserProfile)
async def get_me(user: UserProfile = Depends(get_current_user)):
    return user


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "fastapi_auth_service"}
