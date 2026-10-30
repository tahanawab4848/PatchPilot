"""
Shared response envelopes and error schemas.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None


class DataResponse(BaseModel, Generic[T]):
    data: T
    request_id: str | None = None
