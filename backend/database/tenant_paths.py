from __future__ import annotations

from pathlib import Path

from backend.database.paths import resolve_auth_db_path


def normalize_company_id(company_id: int | str) -> int:
    value = int(company_id)
    if value <= 0:
        raise ValueError("company_id_must_be_positive")
    return value


def tenant_key_for_company(company_id: int | str) -> str:
    cid = normalize_company_id(company_id)
    return f"company_{cid}"


def resolve_tenant_db_root(base_db_path: str | Path | None = None) -> Path:
    """
    Resolve tenant database root directory based on the auth DB location.

    Example:
    - base auth db: data/auth.db
    - tenant root:  data/tenants
    """
    base = resolve_auth_db_path(base_db_path)
    # Keep the production/default layout stable for the canonical auth.db path.
    # For isolated E2E or custom auth DB filenames that share the same parent
    # directory, derive a distinct tenant root so parallel runs do not collide on
    # the same tenant auth.db files.
    if base.name == "auth.db":
        return base.parent / "tenants"
    safe_stem = "".join(
        ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
        for ch in base.stem
    ).strip("._")
    if not safe_stem:
        safe_stem = "auth"
    return base.parent / f"tenants__{safe_stem}"


def resolve_tenant_auth_db_path(company_id: int | str, base_db_path: str | Path | None = None) -> Path:
    tenant_root = resolve_tenant_db_root(base_db_path=base_db_path)
    tenant_key = tenant_key_for_company(company_id)
    return tenant_root / tenant_key / "auth.db"
