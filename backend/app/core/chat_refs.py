from __future__ import annotations

from dataclasses import dataclass

from backend.app.dependencies import AppDependencies


@dataclass(frozen=True)
class ChatRefInfo:
    ref: str
    canonical: str
    raw_id: str
    variants: tuple[str, ...]


def _raw_id(ref: str) -> str:
    if ref.startswith("chat_"):
        return ref[5:]
    if ref.startswith("agent_"):
        return ref[6:]
    return ref


def resolve_chat_ref(deps: AppDependencies, chat_ref: str) -> ChatRefInfo:
    if not isinstance(chat_ref, str):
        chat_ref = str(chat_ref)

    canonical = chat_ref
    ragflow_chat_service = getattr(deps, "ragflow_chat_service", None)
    normalize_chat_ref = getattr(ragflow_chat_service, "normalize_chat_ref", None) if ragflow_chat_service else None
    if callable(normalize_chat_ref):
        try:
            canonical = normalize_chat_ref(chat_ref)
        except Exception:
            canonical = chat_ref

    raw = _raw_id(canonical)
    ordered: list[str] = []
    for candidate in (chat_ref, canonical, raw):
        if isinstance(candidate, str) and candidate and candidate not in ordered:
            ordered.append(candidate)
    return ChatRefInfo(ref=chat_ref, canonical=canonical, raw_id=raw, variants=tuple(ordered))
