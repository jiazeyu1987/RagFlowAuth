from __future__ import annotations

from pydantic import BaseModel

from fastapi import HTTPException


def normalize_user_payload(item: object) -> dict:
    if isinstance(item, BaseModel):
        item = item.model_dump()
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail="user_invalid_payload")
    return item


def wrap_user(item: object) -> dict[str, dict]:
    return {"user": normalize_user_payload(item)}


def wrap_result(message: str) -> dict[str, dict[str, str]]:
    return {"result": {"message": message}}


def run_result_action(action, /, *args, message: str, **kwargs) -> dict[str, dict[str, str]]:
    action(*args, **kwargs)
    return wrap_result(message)


def wrap_user_action(action, /, *args, **kwargs) -> dict[str, dict]:
    return wrap_user(action(*args, **kwargs))
