from pydantic import BaseModel, EmailStr, Field


class UserCredentials(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 3600


class UserProfile(BaseModel):
    username: str
    role: str
    is_active: bool = True
