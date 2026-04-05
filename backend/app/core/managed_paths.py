from __future__ import annotations

from pathlib import Path, PurePosixPath

from .paths import repo_root


def managed_data_root() -> Path:
    return (repo_root() / "data").resolve()


def managed_root_path(root: str | Path) -> Path:
    candidate = Path(root)
    if not candidate.is_absolute():
        candidate = repo_root() / candidate
    resolved = candidate.resolve()
    data_root = managed_data_root()
    if not resolved.is_relative_to(data_root):
        raise ValueError(f"managed root must stay within data/: {root}")
    return resolved


def _invalid_path(field_name: str, reason: str, value: str | Path | None) -> ValueError:
    preview = str(value or "").strip()
    return ValueError(f"invalid {field_name}: {reason}: {preview}")


def _normalize_relative_parts(path: str | Path, *, field_name: str) -> tuple[str, ...]:
    raw = str(path or "").replace("\\", "/").strip()
    if not raw:
        raise _invalid_path(field_name, "path_required", path)

    pure = PurePosixPath(raw)
    if pure.is_absolute():
        raise _invalid_path(field_name, "relative_path_required", path)

    parts: list[str] = []
    for part in pure.parts:
        token = str(part or "").strip()
        if not token or token == ".":
            continue
        if token == "..":
            raise _invalid_path(field_name, "path_escape_not_allowed", path)
        if ":" in token:
            raise _invalid_path(field_name, "drive_segment_not_allowed", path)
        parts.append(token)

    if not parts:
        raise _invalid_path(field_name, "path_required", path)
    return tuple(parts)


def to_managed_data_storage_path(path: str | Path, *, field_name: str = "path") -> str:
    candidate = Path(path)
    repo = repo_root().resolve()
    data_root = managed_data_root()

    if candidate.is_absolute():
        resolved = candidate.resolve()
        if not resolved.is_relative_to(data_root):
            raise _invalid_path(field_name, "managed_data_path_required", path)
        return resolved.relative_to(repo).as_posix()

    parts = _normalize_relative_parts(path, field_name=field_name)
    if parts[0] != "data":
        raise _invalid_path(field_name, "path_must_start_with_data", path)

    resolved = (repo / Path(*parts)).resolve()
    if not resolved.is_relative_to(data_root):
        raise _invalid_path(field_name, "managed_data_path_required", path)
    return PurePosixPath(*parts).as_posix()


def resolve_managed_data_storage_path(path: str | Path, *, field_name: str = "path") -> Path:
    stored = str(path or "").strip()
    if not stored:
        raise _invalid_path(field_name, "path_required", path)
    if Path(stored).is_absolute():
        raise _invalid_path(field_name, "stored_path_must_be_relative", path)
    normalized = to_managed_data_storage_path(stored, field_name=field_name)
    return (repo_root().resolve() / Path(*PurePosixPath(normalized).parts)).resolve()


def to_managed_child_storage_path(
    path: str | Path,
    *,
    managed_root: str | Path,
    field_name: str = "path",
) -> str:
    root = managed_root_path(managed_root)
    candidate = Path(path)

    if candidate.is_absolute():
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise _invalid_path(field_name, "managed_child_path_required", path)
        return resolved.relative_to(root).as_posix()

    parts = _normalize_relative_parts(path, field_name=field_name)
    resolved = (root / Path(*parts)).resolve()
    if not resolved.is_relative_to(root):
        raise _invalid_path(field_name, "managed_child_path_required", path)
    return PurePosixPath(*parts).as_posix()


def resolve_managed_child_storage_path(
    path: str | Path,
    *,
    managed_root: str | Path,
    field_name: str = "path",
) -> Path:
    stored = str(path or "").strip()
    if not stored:
        raise _invalid_path(field_name, "path_required", path)
    if Path(stored).is_absolute():
        raise _invalid_path(field_name, "stored_path_must_be_relative", path)
    normalized = to_managed_child_storage_path(
        stored,
        managed_root=managed_root,
        field_name=field_name,
    )
    return (managed_root_path(managed_root) / Path(*PurePosixPath(normalized).parts)).resolve()
