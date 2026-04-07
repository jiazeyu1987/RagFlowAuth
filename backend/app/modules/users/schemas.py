from __future__ import annotations

from pydantic import BaseModel

from backend.models.user import UserResponse


class ResetPasswordRequest(BaseModel):
    new_password: str


class UserEnvelope(BaseModel):
    user: UserResponse


class ResultEnvelope(BaseModel):
    result: dict[str, str]
