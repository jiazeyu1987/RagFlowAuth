from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def model_validate(model_cls: type[ModelT], payload: Any) -> ModelT:
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


def model_dump(model: BaseModel, *, include_none: bool = True) -> dict[str, Any]:
    exclude_none = not bool(include_none)
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=exclude_none)
    return model.dict(exclude_none=exclude_none)
