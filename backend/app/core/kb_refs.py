from __future__ import annotations

from dataclasses import dataclass

from backend.app.dependencies import AppDependencies


@dataclass(frozen=True)
class KbRefInfo:
    ref: str
    dataset_id: str | None
    name: str | None
    variants: tuple[str, ...]


def resolve_kb_ref(deps: AppDependencies, kb_ref: str) -> KbRefInfo:
    dataset_id: str | None = None
    name: str | None = None

    ragflow_service = getattr(deps, "ragflow_service", None)
    if ragflow_service is not None:
        try:
            normalize_dataset_id = getattr(ragflow_service, "normalize_dataset_id", None)
            if callable(normalize_dataset_id):
                dataset_id = normalize_dataset_id(kb_ref)
        except Exception:
            dataset_id = None
        try:
            resolve_dataset_name = getattr(ragflow_service, "resolve_dataset_name", None)
            if callable(resolve_dataset_name):
                name = resolve_dataset_name(kb_ref)
        except Exception:
            name = None

    ordered: list[str] = []
    for candidate in (kb_ref, dataset_id, name):
        if isinstance(candidate, str) and candidate and candidate not in ordered:
            ordered.append(candidate)

    return KbRefInfo(ref=kb_ref, dataset_id=dataset_id, name=name, variants=tuple(ordered))
