#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.paths import resolve_repo_path
from backend.app.dependencies import create_dependencies
from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService
from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.database.tenant_paths import resolve_tenant_auth_db_path
from backend.models.user import UserCreate, UserUpdate
from backend.runtime.runner import ensure_database
from backend.services.ragflow_config import is_placeholder_api_key
from backend.services.training_compliance import TrainingComplianceError


DEFAULT_ORG_EXCEL_PATH = Path("doc") / "上海瑛泰医疗器械股份有限公司在职员工20260403.xls"
DEFAULT_MANAGED_ROOT_NAME = "E2E Root"
DEFAULT_E2E_DATASET_NAME = "RagflowAuth E2E Dataset"
DEFAULT_E2E_CHAT_NAME = "RagflowAuth E2E Chat"
DEFAULT_E2E_SEED_DOC_PATH = Path("data") / "e2e" / "ragflow" / "ragflowauth-e2e-seed.txt"
DEFAULT_E2E_SEED_DOC_CONTENT = (
    "RagflowAuth E2E seed knowledge base.\n"
    "This document exists so the real doc/e2e assistant always owns at least one parsed file.\n"
    "Keyword: ragflowauth-e2e-seed-anchor.\n"
)
RAGFLOW_DATASET_PAGE_SIZE = 200
RAGFLOW_CHAT_PAGE_SIZE = 200
RAGFLOW_READY_TIMEOUT_S = 60.0
RAGFLOW_READY_POLL_INTERVAL_S = 3.0

VIEWER_GROUP_NAME = "e2e_scope_viewer"
REVIEWER_GROUP_NAME = "e2e_scope_reviewer"
UPLOADER_GROUP_NAME = "e2e_scope_uploader"
OPERATOR_GROUP_NAME = "e2e_scope_operator"


@dataclass(frozen=True)
class EnvUserSpec:
    username: str
    full_name: str
    email: str
    role: str
    password: str


@dataclass(frozen=True)
class BootstrapConfig:
    db_path: Path
    org_excel_path: Path
    admin_username: str
    admin_password: str
    sub_admin_username: str
    sub_admin_password: str
    operator_username: str
    operator_password: str
    viewer_username: str
    viewer_password: str
    reviewer_username: str
    reviewer_password: str
    uploader_username: str
    uploader_password: str
    company_name: str | None
    department_name: str | None
    managed_root_name: str
    dataset_name: str | None
    chat_name: str | None
    json_output: bool


def _require_text(name: str, value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{name}_required")
    return text


def _optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _has_name_override(explicit_name: str | None, *, env_var: str) -> bool:
    return bool(_optional_text(explicit_name) or _optional_text(os.environ.get(env_var)))


def _build_bootstrap_run_tag() -> str:
    return f"{int(time.time() * 1000)}-{os.getpid()}"


def _materialize_bootstrap_resource_name(
    base_name: str,
    *,
    explicit_name: str | None,
    env_var: str,
    run_tag: str,
) -> str:
    clean_base_name = _optional_text(base_name)
    if not clean_base_name:
        raise RuntimeError("bootstrap_resource_name_required")
    if _has_name_override(explicit_name, env_var=env_var):
        return clean_base_name
    return f"{clean_base_name} [{run_tag}]"


def _is_managed_bootstrap_resource_name(name: str | None, *, base_name: str) -> bool:
    clean_name = _optional_text(name)
    clean_base_name = _optional_text(base_name)
    if not clean_name or not clean_base_name:
        return False
    return clean_name == clean_base_name or clean_name.startswith(f"{clean_base_name} [")


def _assert_isolated_db_path(db_path: Path) -> None:
    main_db_path = resolve_auth_db_path(Path("data") / "auth.db").resolve()
    resolved = db_path.resolve()
    if resolved == main_db_path:
        raise RuntimeError(
            f"refusing_to_bootstrap_main_db: target={resolved}; use an isolated DB such as "
            f"{resolve_auth_db_path(Path('data') / 'e2e' / 'auth.db')}"
        )


def _reset_isolated_db_tree(db_path: Path) -> None:
    resolved_db_path = resolve_auth_db_path(db_path).resolve()
    tenant_root = resolve_tenant_auth_db_path(company_id=1, base_db_path=resolved_db_path).resolve().parents[1]
    if tenant_root.parent != resolved_db_path.parent:
        raise RuntimeError(
            f"unexpected_tenant_root_layout: db={resolved_db_path}; tenant_root={tenant_root}"
        )

    for suffix in ("", "-shm", "-wal"):
        target = Path(f"{resolved_db_path}{suffix}")
        if target.exists():
            target.unlink()

    if tenant_root.exists():
        shutil.rmtree(tenant_root)


def _resolve_org_excel_path(raw_path: str | None) -> Path:
    candidate = resolve_repo_path(raw_path) if raw_path else resolve_repo_path(DEFAULT_ORG_EXCEL_PATH)
    resolved = Path(candidate).resolve()
    if not resolved.exists():
        raise RuntimeError(f"org_excel_not_found:{resolved}")
    return resolved


def _infer_company_name_from_excel_path(excel_path: Path) -> str | None:
    stem = str(excel_path.stem or "").strip()
    marker = "在职员工"
    if marker in stem:
        inferred = stem.split(marker, 1)[0].strip()
        if inferred:
            return inferred
    return None


def _build_users(config: BootstrapConfig) -> dict[str, EnvUserSpec]:
    return {
        "sub_admin": EnvUserSpec(
            username=config.sub_admin_username,
            full_name="E2E Sub Admin",
            email=f"{config.sub_admin_username}@example.test",
            role="sub_admin",
            password=config.sub_admin_password,
        ),
        "operator": EnvUserSpec(
            username=config.operator_username,
            full_name="E2E Operator",
            email=f"{config.operator_username}@example.test",
            role="operator",
            password=config.operator_password,
        ),
        "viewer": EnvUserSpec(
            username=config.viewer_username,
            full_name="E2E Viewer",
            email=f"{config.viewer_username}@example.test",
            role="viewer",
            password=config.viewer_password,
        ),
        "reviewer": EnvUserSpec(
            username=config.reviewer_username,
            full_name="E2E Reviewer",
            email=f"{config.reviewer_username}@example.test",
            role="reviewer",
            password=config.reviewer_password,
        ),
        # The system has no dedicated "uploader" role. Keep the account in the
        # viewer role and grant upload capability through a tenant permission group.
        "uploader": EnvUserSpec(
            username=config.uploader_username,
            full_name="E2E Uploader",
            email=f"{config.uploader_username}@example.test",
            role="viewer",
            password=config.uploader_password,
        ),
    }


def _clear_user_scope_fields(user_store: Any, *, user_id: str) -> None:
    conn = user_store._get_connection()
    try:
        conn.execute(
            """
            UPDATE users
            SET manager_user_id = NULL,
                company_id = NULL,
                department_id = NULL,
                managed_kb_root_node_id = NULL
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _ensure_admin_user(user_store: Any, *, username: str, password: str) -> Any:
    existing = user_store.get_by_username(username)
    email = f"{username}@example.test"
    if existing is None:
        user = user_store.create_user(
            username=username,
            password=password,
            full_name="E2E Admin",
            email=email,
            role="admin",
            status="active",
            created_by="system",
        )
    else:
        user = user_store.update_user(
            existing.user_id,
            full_name="E2E Admin",
            email=email,
            role="admin",
            status="active",
            max_login_sessions=3,
            idle_timeout_minutes=120,
            can_change_password=True,
            disable_login_enabled=False,
            electronic_signature_enabled=True,
            managed_kb_root_node_id="",
        )
        if user is None:
            raise RuntimeError(f"admin_update_failed:{username}")
        _clear_user_scope_fields(user_store, user_id=user.user_id)
    user_store.update_password(user.user_id, password)
    user_store.set_user_permission_groups(user.user_id, [])
    refreshed = user_store.get_by_user_id(user.user_id)
    if refreshed is None:
        raise RuntimeError(f"admin_reload_failed:{username}")
    return refreshed


def _ensure_bootstrap_employee_profile(
    *,
    db_path: Path,
    employee_user_id: str,
    full_name: str,
    email: str | None,
    company_id: int,
    department_id: int,
) -> None:
    clean_employee_user_id = str(employee_user_id or "").strip()
    clean_full_name = str(full_name or "").strip()
    if not clean_employee_user_id:
        raise RuntimeError("bootstrap_employee_user_id_required")
    if not clean_full_name:
        raise RuntimeError(f"bootstrap_employee_full_name_required:{clean_employee_user_id}")
    if department_id is None:
        raise RuntimeError(f"bootstrap_department_required_for_employee:{clean_employee_user_id}")

    clean_email = str(email or "").strip() or None
    source_key = f"bootstrap:{clean_employee_user_id}"
    now_ms = int(time.time() * 1000)

    conn = connect_sqlite(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        employee_row = conn.execute(
            """
            SELECT employee_id, source_key, name, company_id, department_id
            FROM org_employees
            WHERE employee_user_id = ?
            ORDER BY employee_id ASC
            LIMIT 1
            """,
            (clean_employee_user_id,),
        ).fetchone()

        if employee_row is not None:
            existing_source_key = str(employee_row[1] or "").strip()
            existing_full_name = str(employee_row[2] or "").strip()
            existing_company_id = int(employee_row[3] or 0)
            existing_department_id = int(employee_row[4] or 0)
            if (
                existing_source_key != source_key
                and (
                    existing_full_name != clean_full_name
                    or existing_company_id != int(company_id)
                    or existing_department_id != int(department_id)
                )
            ):
                raise RuntimeError(f"bootstrap_employee_user_id_conflict:{clean_employee_user_id}")

        profile_row = conn.execute(
            """
            SELECT employee_id
            FROM org_employees
            WHERE source_key = ?
            LIMIT 1
            """,
            (source_key,),
        ).fetchone()

        if profile_row is None:
            conn.execute(
                """
                INSERT INTO org_employees (
                    employee_user_id,
                    name,
                    email,
                    employee_no,
                    department_manager_name,
                    is_department_manager,
                    company_id,
                    department_id,
                    source_key,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, NULL, NULL, 0, ?, ?, ?, 0, ?, ?)
                """,
                (
                    clean_employee_user_id,
                    clean_full_name,
                    clean_email,
                    int(company_id),
                    int(department_id),
                    source_key,
                    now_ms,
                    now_ms,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE org_employees
                SET employee_user_id = ?,
                    name = ?,
                    email = ?,
                    employee_no = NULL,
                    department_manager_name = NULL,
                    is_department_manager = 0,
                    company_id = ?,
                    department_id = ?,
                    sort_order = 0,
                    updated_at_ms = ?
                WHERE employee_id = ?
                """,
                (
                    clean_employee_user_id,
                    clean_full_name,
                    clean_email,
                    int(company_id),
                    int(department_id),
                    now_ms,
                    int(profile_row[0]),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_bootstrap_employee_profiles(
    *,
    db_path: Path,
    specs: list[EnvUserSpec],
    company_id: int,
    department_id: int | None,
) -> None:
    if department_id is None:
        raise RuntimeError("bootstrap_department_required_for_user_seed")
    for spec in specs:
        _ensure_bootstrap_employee_profile(
            db_path=db_path,
            employee_user_id=spec.username,
            full_name=spec.full_name,
            email=spec.email,
            company_id=int(company_id),
            department_id=int(department_id),
        )


def _rebuild_org(global_deps: Any, *, actor_user_id: str, excel_path: Path) -> dict[str, Any]:
    summary = global_deps.org_structure_manager.rebuild_from_excel(
        actor_user_id=actor_user_id,
        excel_path=str(excel_path),
        source_label=str(excel_path),
    )
    if not global_deps.org_structure_manager.list_companies():
        raise RuntimeError(f"org_rebuild_produced_no_companies:{excel_path}")
    return {
        "company_created": int(getattr(summary, "company_created", 0) or 0),
        "company_updated": int(getattr(summary, "company_updated", 0) or 0),
        "department_created": int(getattr(summary, "department_created", 0) or 0),
        "department_updated": int(getattr(summary, "department_updated", 0) or 0),
        "employee_created": int(getattr(summary, "employee_created", 0) or 0),
        "employee_updated": int(getattr(summary, "employee_updated", 0) or 0),
        "source": str(excel_path),
    }


def _select_company(global_deps: Any, *, company_name: str | None, excel_path: Path) -> Any:
    companies = list(global_deps.org_structure_manager.list_companies() or [])
    if not companies:
        raise RuntimeError("org_company_not_found")
    requested_name = company_name or _infer_company_name_from_excel_path(excel_path)
    if requested_name:
        for company in companies:
            if str(getattr(company, "name", "") or "").strip() == requested_name:
                return company
        available = ",".join(sorted(str(getattr(item, "name", "") or "").strip() for item in companies)[:10])
        raise RuntimeError(f"company_not_found:{requested_name}; available={available}")
    if len(companies) == 1:
        return companies[0]
    available = ",".join(sorted(str(getattr(item, "name", "") or "").strip() for item in companies)[:10])
    raise RuntimeError(f"company_name_required: available={available}")


def _select_department(global_deps: Any, *, company_id: int, department_name: str | None) -> Any | None:
    departments = [
        item
        for item in (global_deps.org_structure_manager.list_departments_flat() or [])
        if int(getattr(item, "company_id", 0) or 0) == company_id
    ]
    if not departments:
        if department_name:
            raise RuntimeError(f"department_not_found_for_company:{company_id}")
        return None
    if department_name:
        for department in departments:
            if str(getattr(department, "name", "") or "").strip() == department_name:
                return department
        available = ",".join(sorted(str(getattr(item, "name", "") or "").strip() for item in departments)[:20])
        raise RuntimeError(f"department_not_found:{department_name}; available={available}")
    return sorted(
        departments,
        key=lambda item: (
            int(getattr(item, "level_no", 0) or 0),
            int(getattr(item, "sort_order", 0) or 0),
            str(getattr(item, "path_name", "") or ""),
            int(getattr(item, "department_id", 0) or 0),
        ),
    )[0]


def _ensure_bootstrap_department(*, db_path: Path, company_id: int, company_name: str) -> int:
    clean_company_name = str(company_name or "").strip()
    if not clean_company_name:
        raise RuntimeError("bootstrap_company_name_required")
    source_key = f"bootstrap:department:{int(company_id)}"
    department_name = "E2E Seed Department"
    path_name = f"{clean_company_name} / {department_name}"
    now_ms = int(time.time() * 1000)

    conn = connect_sqlite(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT department_id
            FROM departments
            WHERE source_key = ?
            LIMIT 1
            """,
            (source_key,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO departments (
                    name,
                    company_id,
                    parent_department_id,
                    source_key,
                    source_department_id,
                    level_no,
                    path_name,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, NULL, ?, NULL, 2, ?, 0, ?, ?)
                """,
                (
                    department_name,
                    int(company_id),
                    source_key,
                    path_name,
                    now_ms,
                    now_ms,
                ),
            )
            row = conn.execute("SELECT last_insert_rowid()").fetchone()
            if row is None:
                raise RuntimeError("bootstrap_department_insert_failed")
            department_id = int(row[0])
        else:
            department_id = int(row[0])
            conn.execute(
                """
                UPDATE departments
                SET name = ?,
                    company_id = ?,
                    parent_department_id = NULL,
                    source_department_id = NULL,
                    level_no = 2,
                    path_name = ?,
                    sort_order = 0,
                    updated_at_ms = ?
                WHERE department_id = ?
                """,
                (
                    department_name,
                    int(company_id),
                    path_name,
                    now_ms,
                    department_id,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return int(department_id)


def _ensure_managed_root_node(tenant_deps: Any, *, root_name: str, created_by: str) -> str:
    for node in tenant_deps.knowledge_directory_store.list_nodes():
        if str(node.get("parent_id") or "").strip():
            continue
        if str(node.get("name") or "").strip() != root_name:
            continue
        node_id = str(node.get("node_id") or "").strip()
        if node_id:
            return node_id
    created = tenant_deps.knowledge_directory_store.create_node(root_name, None, created_by=created_by)
    node_id = str(created.get("node_id") or "").strip()
    if not node_id:
        raise RuntimeError("managed_root_node_create_failed")
    return node_id


def _probe_ragflow_datasets(ragflow_service: Any) -> list[dict[str, Any]]:
    base_url = str(ragflow_service.config.get("base_url") or "").strip()
    api_key = str(ragflow_service.config.get("api_key") or "").strip()
    timeout_s = float(ragflow_service.config.get("timeout", 10) or 10)
    if not base_url:
        raise RuntimeError("ragflow_base_url_missing")
    if is_placeholder_api_key(api_key):
        raise RuntimeError("ragflow_api_key_not_configured")
    datasets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    page = 1
    while True:
        response = requests.get(
            f"{base_url.rstrip('/')}/api/v1/datasets",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"page": page, "page_size": RAGFLOW_DATASET_PAGE_SIZE},
            timeout=timeout_s,
        )
        if response.status_code != 200:
            raise RuntimeError(f"ragflow_probe_http_{response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("ragflow_probe_invalid_payload")
        if payload.get("code") not in (0, None):
            raise RuntimeError(f"ragflow_probe_failed:{payload.get('message') or 'unknown'}")
        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError("ragflow_probe_invalid_data")
        batch = [item for item in data if isinstance(item, dict)]
        for item in batch:
            item_id = str(item.get("id") or "").strip()
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            datasets.append(item)
        if len(batch) < RAGFLOW_DATASET_PAGE_SIZE:
            break
        page += 1
    return datasets


def _list_ragflow_chats(tenant_deps: Any, *, name: str | None = None) -> list[dict[str, Any]]:
    chats: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    page = 1
    while True:
        try:
            batch = tenant_deps.ragflow_chat_service.list_chats(page=page, page_size=RAGFLOW_CHAT_PAGE_SIZE, name=name)
        except Exception as exc:
            raise RuntimeError(f"ragflow_chat_probe_failed:{exc}") from exc
        if not isinstance(batch, list):
            raise RuntimeError("ragflow_chat_probe_invalid_payload")
        normalized = [item for item in batch if isinstance(item, dict)]
        for item in normalized:
            chat_id = str(item.get("id") or "").strip()
            if chat_id and chat_id in seen_ids:
                continue
            if chat_id:
                seen_ids.add(chat_id)
            chats.append(item)
        if len(normalized) < RAGFLOW_CHAT_PAGE_SIZE:
            break
        page += 1
    return chats


def _resolve_dataset_content_count(dataset: dict[str, Any]) -> int:
    for key in ("chunk_count", "chunk_num", "document_count", "doc_num", "token_num"):
        raw = dataset.get(key)
        try:
            count = int(raw)
        except (TypeError, ValueError):
            continue
        if count > 0:
            return count
    return 0


def _build_dataset_create_payload(*, existing_datasets: list[dict[str, Any]], dataset_name: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": dataset_name}
    for item in existing_datasets:
        chunk_method = _optional_text(item.get("chunk_method") or item.get("parser_id"))
        embedding_model = _optional_text(item.get("embedding_model") or item.get("embd_id"))
        if chunk_method and "chunk_method" not in payload:
            payload["chunk_method"] = chunk_method
        if embedding_model and "embedding_model" not in payload:
            payload["embedding_model"] = embedding_model
        if "chunk_method" in payload and "embedding_model" in payload:
            break
    return payload


def _ensure_ragflow_seed_file() -> Path:
    seed_path = resolve_repo_path(DEFAULT_E2E_SEED_DOC_PATH).resolve()
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    if not seed_path.exists():
        seed_path.write_text(DEFAULT_E2E_SEED_DOC_CONTENT, encoding="utf-8", newline="\n")
    return seed_path


def _document_str_field(document: dict[str, Any] | None, key: str) -> str:
    if not isinstance(document, dict):
        return ""
    return str(document.get(key) or "").strip()


def _cleanup_dataset_documents(
    tenant_deps: Any,
    *,
    dataset_info: dict[str, str],
    keep_filenames: set[str],
) -> list[dict[str, Any]]:
    dataset_id = str(dataset_info.get("id") or "").strip()
    dataset_name = str(dataset_info.get("name") or "").strip()
    if not dataset_id or not dataset_name:
        raise RuntimeError("ragflow_dataset_info_invalid")

    documents = [
        item
        for item in tenant_deps.ragflow_service.list_documents(dataset_id)
        if isinstance(item, dict)
    ]
    retained_names: set[str] = set()
    delete_targets: list[tuple[str, str]] = []
    for item in documents:
        doc_name = _document_str_field(item, "name")
        doc_id = _document_str_field(item, "id")
        if doc_name in keep_filenames and doc_name not in retained_names:
            if not doc_id:
                raise RuntimeError(
                    f"ragflow_dataset_keep_document_missing_id:{dataset_name}; name={doc_name or 'unknown'}"
                )
            retained_names.add(doc_name)
            continue
        if not doc_id:
            raise RuntimeError(
                f"ragflow_dataset_cleanup_document_missing_id:{dataset_name}; name={doc_name or 'unknown'}"
            )
        delete_targets.append((doc_id, doc_name))

    for doc_id, doc_name in delete_targets:
        deleted = tenant_deps.ragflow_service.delete_document(doc_id, dataset_name=dataset_id)
        if not deleted:
            raise RuntimeError(
                f"ragflow_dataset_cleanup_delete_failed:{dataset_name}; document_id={doc_id}; name={doc_name or 'unknown'}"
            )

    return [
        item
        for item in tenant_deps.ragflow_service.list_documents(dataset_id)
        if isinstance(item, dict)
    ]


def _wait_for_dataset_ready(
    tenant_deps: Any,
    *,
    dataset_id: str,
    dataset_name: str,
    context_doc_id: str | None = None,
) -> dict[str, str]:
    deadline = time.time() + RAGFLOW_READY_TIMEOUT_S
    last_status = "unknown"
    while True:
        datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
        dataset = next(
            (
                item
                for item in datasets
                if str(item.get("id") or "").strip() == dataset_id
                or str(item.get("name") or "").strip() == dataset_name
            ),
            None,
        )
        if dataset is not None and _resolve_dataset_content_count(dataset) > 0:
            resolved_id = str(dataset.get("id") or dataset_id).strip() or dataset_id
            resolved_name = str(dataset.get("name") or dataset_name).strip() or dataset_name
            return {"id": resolved_id, "name": resolved_name}

        documents = tenant_deps.ragflow_service.list_documents(dataset_id)
        if context_doc_id:
            for item in documents:
                if str(item.get("id") or "").strip() == context_doc_id:
                    last_status = str(item.get("status") or "unknown").strip() or "unknown"
                    break
        elif documents:
            last_status = ",".join(
                sorted({str(item.get("status") or "unknown").strip() or "unknown" for item in documents})
            )

        if time.time() >= deadline:
            raise RuntimeError(
                f"ragflow_dataset_not_ready:{dataset_name}({dataset_id}); document_status={last_status}"
            )
        time.sleep(RAGFLOW_READY_POLL_INTERVAL_S)


def _ensure_dataset_seed_content(tenant_deps: Any, *, dataset_info: dict[str, str]) -> dict[str, str]:
    dataset_id = str(dataset_info.get("id") or "").strip()
    dataset_name = str(dataset_info.get("name") or "").strip()
    if not dataset_id or not dataset_name:
        raise RuntimeError("ragflow_dataset_info_invalid")

    seed_path = _ensure_ragflow_seed_file()
    documents = _cleanup_dataset_documents(
        tenant_deps,
        dataset_info={"id": dataset_id, "name": dataset_name},
        keep_filenames={seed_path.name},
    )
    seed_doc = next(
        (item for item in documents if _document_str_field(item, "name") == seed_path.name),
        None,
    )
    doc_id = _document_str_field(seed_doc, "id")

    datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
    dataset = next(
        (
            item
            for item in datasets
            if str(item.get("id") or "").strip() == dataset_id
            or str(item.get("name") or "").strip() == dataset_name
        ),
        None,
    )
    if seed_doc is not None and dataset is not None and _resolve_dataset_content_count(dataset) > 0:
        return {"id": dataset_id, "name": dataset_name}

    if not doc_id:
        uploaded_doc_id = tenant_deps.ragflow_service.upload_document(str(seed_path), kb_id=dataset_id)
        doc_id = str(uploaded_doc_id or "").strip()
        if not doc_id or doc_id == "uploaded":
            documents = tenant_deps.ragflow_service.list_documents(dataset_id)
            seed_doc = next(
                (item for item in documents if str(item.get("name") or "").strip() == seed_path.name),
                None,
            )
            doc_id = str(seed_doc.get("id") or "").strip() if isinstance(seed_doc, dict) else ""
        if not doc_id:
            raise RuntimeError(f"ragflow_seed_upload_failed:{dataset_name}")

    if not tenant_deps.ragflow_service.parse_document(dataset_ref=dataset_id, document_id=doc_id):
        raise RuntimeError(f"ragflow_seed_parse_failed:{dataset_name}; document_id={doc_id}")

    return _wait_for_dataset_ready(
        tenant_deps,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        context_doc_id=doc_id,
    )


def _extract_chat_dataset_refs(chat: dict[str, Any]) -> tuple[set[str], set[str]]:
    linked_ids: set[str] = set()
    linked_names: set[str] = set()
    for key in ("dataset_ids", "kb_ids"):
        raw = chat.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            ref = str(item or "").strip()
            if ref:
                linked_ids.add(ref)
    for item in (chat.get("datasets") or []):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        item_name = str(item.get("name") or "").strip()
        if item_id:
            linked_ids.add(item_id)
        if item_name:
            linked_names.add(item_name)
    return linked_ids, linked_names


def _resolve_dataset_name(tenant_deps: Any, explicit_name: str | None) -> str:
    explicit = _optional_text(explicit_name)
    if explicit:
        return explicit
    env_name = _optional_text(os.environ.get("E2E_REAL_DATASET_NAME"))
    if env_name:
        return env_name
    return DEFAULT_E2E_DATASET_NAME


def _resolve_chat_name(tenant_deps: Any, explicit_name: str | None) -> str:
    explicit = _optional_text(explicit_name)
    if explicit:
        return explicit
    env_name = _optional_text(os.environ.get("E2E_REAL_CHAT_NAME"))
    if env_name:
        return env_name
    return DEFAULT_E2E_CHAT_NAME


def _ensure_dataset_binding(tenant_deps: Any, *, node_id: str, dataset_name: str) -> dict[str, str]:
    datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
    dataset = next((item for item in datasets if str(item.get("name") or "").strip() == dataset_name), None)
    if dataset is None:
        payload = _build_dataset_create_payload(existing_datasets=datasets, dataset_name=dataset_name)
        try:
            created = tenant_deps.ragflow_service.create_dataset(payload)
        except Exception as exc:
            raise RuntimeError(f"ragflow_dataset_create_failed:{dataset_name}; {exc}") from exc
        dataset = created if isinstance(created, dict) else None
        if dataset is None:
            datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
            dataset = next((item for item in datasets if str(item.get("name") or "").strip() == dataset_name), None)
        if dataset is None:
            raise RuntimeError(f"ragflow_dataset_create_missing:{dataset_name}")
    dataset_id = str(dataset.get("id") or "").strip()
    resolved_name = str(dataset.get("name") or dataset_name).strip() or dataset_name
    if not dataset_id:
        raise RuntimeError(f"ragflow_dataset_missing_id:{dataset_name}")
    tenant_deps.knowledge_directory_store.assign_dataset(dataset_id, node_id)
    return _ensure_dataset_seed_content(tenant_deps, dataset_info={"id": dataset_id, "name": resolved_name})


def _ensure_chat_target(tenant_deps: Any, *, chat_name: str, dataset_info: dict[str, str]) -> dict[str, Any]:
    dataset_id = str(dataset_info.get("id") or "").strip()
    dataset_name = str(dataset_info.get("name") or "").strip()
    if not dataset_id or not dataset_name:
        raise RuntimeError("ragflow_dataset_info_invalid")

    matches = _list_ragflow_chats(tenant_deps, name=chat_name)
    chat = next((item for item in matches if str(item.get("name") or "").strip() == chat_name), None)
    if chat is None:
        create_payload = {"name": chat_name, "dataset_ids": [dataset_id]}
        for create_attempt in range(1, 4):
            try:
                created = tenant_deps.ragflow_chat_service.create_chat(create_payload)
            except Exception as exc:
                if "chat_dataset_not_ready" in str(exc):
                    _wait_for_dataset_ready(
                        tenant_deps,
                        dataset_id=dataset_id,
                        dataset_name=dataset_name,
                    )
                    if create_attempt < 3:
                        time.sleep(RAGFLOW_READY_POLL_INTERVAL_S)
                        continue
                raise RuntimeError(f"ragflow_chat_create_failed:{chat_name}; {exc}") from exc

            chat = created if isinstance(created, dict) else None
            if chat is None or not str(chat.get("id") or "").strip():
                matches = _list_ragflow_chats(tenant_deps, name=chat_name)
                chat = next((item for item in matches if str(item.get("name") or "").strip() == chat_name), None)
            if chat is not None:
                break
        if chat is None:
            raise RuntimeError(f"ragflow_chat_create_missing:{chat_name}")

    linked, linked_names = _extract_chat_dataset_refs(chat)
    if dataset_id not in linked and dataset_name not in linked_names:
        chat_id = str(chat.get("id") or "").strip()
        if not chat_id:
            raise RuntimeError(f"ragflow_chat_missing_id:{chat_name}")
        try:
            updated = tenant_deps.ragflow_chat_service.update_chat(
                chat_id,
                {"name": chat_name, "dataset_ids": [dataset_id]},
            )
        except Exception:
            try:
                tenant_deps.ragflow_chat_service.clear_chat_parsed_files(chat_id)
                updated = tenant_deps.ragflow_chat_service.update_chat(
                    chat_id,
                    {"name": chat_name, "dataset_ids": [dataset_id]},
                )
            except Exception as rebind_exc:
                raise RuntimeError(
                    f"ragflow_chat_rebind_failed:{chat_name}; {rebind_exc}"
                ) from rebind_exc
        chat = updated if isinstance(updated, dict) else None
        if chat is None:
            matches = _list_ragflow_chats(tenant_deps, name=chat_name)
            chat = next((item for item in matches if str(item.get("name") or "").strip() == chat_name), None)
        if chat is None:
            raise RuntimeError(f"ragflow_chat_rebind_missing:{chat_name}")
        linked, linked_names = _extract_chat_dataset_refs(chat)
        if dataset_id not in linked and dataset_name not in linked_names:
            raise RuntimeError(
                f"ragflow_chat_dataset_mismatch:{chat_name}; expected_dataset={dataset_name}({dataset_id})"
            )

    chat_id = str(chat.get("id") or "").strip()
    if not chat_id:
        raise RuntimeError(f"ragflow_chat_missing_id:{chat_name}")
    return {"id": chat_id, "name": chat_name}


def _unbind_previous_managed_dataset_bindings(tenant_deps: Any, *, active_dataset_id: str) -> None:
    clean_active_id = str(active_dataset_id or "").strip()
    if not clean_active_id:
        raise RuntimeError("ragflow_dataset_missing_id")

    for item in _probe_ragflow_datasets(tenant_deps.ragflow_service):
        dataset_id = str(item.get("id") or "").strip()
        dataset_name = str(item.get("name") or "").strip()
        if not dataset_id or dataset_id == clean_active_id:
            continue
        if not _is_managed_bootstrap_resource_name(dataset_name, base_name=DEFAULT_E2E_DATASET_NAME):
            continue
        tenant_deps.knowledge_directory_store.assign_dataset(dataset_id, None)


def _ensure_owned_group(
    tenant_deps: Any,
    *,
    owner_user_id: str,
    group_name: str,
    description: str,
    accessible_kb_nodes: list[str],
    can_upload: bool,
    can_review: bool,
    can_download: bool,
    can_copy: bool,
    can_delete: bool,
    can_manage_kb_directory: bool,
    can_view_kb_config: bool,
    can_view_tools: bool,
) -> int:
    store = tenant_deps.permission_group_store
    existing = store.get_group_by_name(group_name)
    if existing is not None:
        owner = str(existing.get("created_by") or "").strip()
        if owner != owner_user_id:
            raise RuntimeError(f"permission_group_owner_conflict:{group_name}")
        ok = store.update_group(
            int(existing["group_id"]),
            group_name=group_name,
            description=description,
            accessible_kbs=[],
            accessible_kb_nodes=accessible_kb_nodes,
            accessible_chats=[],
            accessible_tools=[],
            can_upload=can_upload,
            can_review=can_review,
            can_download=can_download,
            can_copy=can_copy,
            can_delete=can_delete,
            can_manage_kb_directory=can_manage_kb_directory,
            can_view_kb_config=can_view_kb_config,
            can_view_tools=can_view_tools,
        )
        if not ok:
            raise RuntimeError(f"permission_group_update_failed:{group_name}")
        return int(existing["group_id"])
    group_id = store.create_group(
        group_name=group_name,
        description=description,
        created_by=owner_user_id,
        accessible_kbs=[],
        accessible_kb_nodes=accessible_kb_nodes,
        accessible_chats=[],
        accessible_tools=[],
        can_upload=can_upload,
        can_review=can_review,
        can_download=can_download,
        can_copy=can_copy,
        can_delete=can_delete,
        can_manage_kb_directory=can_manage_kb_directory,
        can_view_kb_config=can_view_kb_config,
        can_view_tools=can_view_tools,
    )
    if not group_id:
        raise RuntimeError(f"permission_group_create_failed:{group_name}")
    return int(group_id)


def _create_payload(
    spec: EnvUserSpec,
    *,
    company_id: int,
    department_id: int | None,
    manager_user_id: str | None,
    managed_kb_root_node_id: str | None,
    group_ids: list[int] | None,
) -> UserCreate:
    return UserCreate(
        username=spec.username,
        password=spec.password,
        employee_user_id=spec.username,
        full_name=spec.full_name,
        email=spec.email,
        manager_user_id=manager_user_id,
        company_id=company_id,
        department_id=department_id,
        role=spec.role,
        group_ids=group_ids,
        status="active",
        max_login_sessions=3,
        idle_timeout_minutes=120,
        can_change_password=True,
        disable_login_enabled=False,
        managed_kb_root_node_id=managed_kb_root_node_id,
        electronic_signature_enabled=True,
    )


def _update_payload(
    spec: EnvUserSpec,
    *,
    company_id: int,
    department_id: int | None,
    manager_user_id: str | None,
    managed_kb_root_node_id: str | None,
    group_ids: list[int] | None,
) -> UserUpdate:
    return UserUpdate(
        full_name=spec.full_name,
        email=spec.email,
        manager_user_id=(manager_user_id if manager_user_id is not None else ""),
        company_id=company_id,
        department_id=department_id,
        role=spec.role,
        group_ids=group_ids,
        status="active",
        max_login_sessions=3,
        idle_timeout_minutes=120,
        can_change_password=True,
        disable_login_enabled=False,
        managed_kb_root_node_id=managed_kb_root_node_id,
        electronic_signature_enabled=True,
    )


def _upsert_user(
    *,
    users_service: UsersService,
    user_store: Any,
    created_by: str,
    spec: EnvUserSpec,
    company_id: int,
    department_id: int | None,
    manager_user_id: str | None,
    managed_kb_root_node_id: str | None,
    group_ids: list[int] | None,
    assign_groups_after_create: bool,
) -> Any:
    existing = user_store.get_by_username(spec.username)
    if existing is None:
        created = users_service.create_user(
            user_data=_create_payload(
                spec,
                company_id=company_id,
                department_id=department_id,
                manager_user_id=manager_user_id,
                managed_kb_root_node_id=managed_kb_root_node_id,
                group_ids=None if assign_groups_after_create else group_ids,
            ),
            created_by=created_by,
        )
        user_id = str(created.user_id)
    else:
        updated = users_service.update_user(
            user_id=existing.user_id,
            user_data=_update_payload(
                spec,
                company_id=company_id,
                department_id=department_id,
                manager_user_id=manager_user_id,
                managed_kb_root_node_id=managed_kb_root_node_id,
                group_ids=None if assign_groups_after_create else group_ids,
            ),
        )
        user_id = str(updated.user_id)
    user_store.update_password(user_id, spec.password)
    if assign_groups_after_create:
        users_service.update_user(user_id=user_id, user_data=UserUpdate(group_ids=list(group_ids or [])))
    refreshed = user_store.get_by_user_id(user_id)
    if refreshed is None:
        raise RuntimeError(f"user_missing_after_upsert:{spec.username}")
    return refreshed


def _seed_training_if_needed(
    training_service: Any,
    *,
    user_id: str,
    role_code: str,
    controlled_action: str,
    actor_user_id: str,
) -> dict[str, Any]:
    try:
        status = training_service.evaluate_action_status(
            user_id=user_id,
            role_code=role_code,
            controlled_action=controlled_action,
        )
        if bool(status.get("allowed")):
            return status
    except TrainingComplianceError:
        pass

    requirements = training_service.list_requirements(controlled_action=controlled_action, limit=20)
    if not requirements:
        raise RuntimeError(f"training_requirement_not_configured:{controlled_action}")

    requirement = requirements[0]
    now_ms = int(time.time() * 1000)
    one_year_ms = 365 * 24 * 60 * 60 * 1000
    completed_at_ms = now_ms - 60_000

    training_service.record_training(
        requirement_code=str(requirement["requirement_code"]),
        user_id=user_id,
        curriculum_version=str(requirement["curriculum_version"]),
        trainer_user_id=actor_user_id,
        training_outcome="passed",
        effectiveness_status="effective",
        effectiveness_score=100.0,
        effectiveness_summary="Seeded by bootstrap_real_test_env",
        training_notes="real_e2e_seed",
        completed_at_ms=completed_at_ms,
        effectiveness_reviewed_by_user_id=actor_user_id,
        effectiveness_reviewed_at_ms=completed_at_ms,
    )
    training_service.grant_certification(
        requirement_code=str(requirement["requirement_code"]),
        user_id=user_id,
        granted_by_user_id=actor_user_id,
        certification_status="active",
        valid_until_ms=now_ms + one_year_ms,
        certification_notes="real_e2e_seed",
        granted_at_ms=completed_at_ms,
    )
    status = training_service.evaluate_action_status(
        user_id=user_id,
        role_code=role_code,
        controlled_action=controlled_action,
    )
    if not bool(status.get("allowed")):
        raise RuntimeError(f"training_seed_failed:{controlled_action}:{user_id}")
    return status


def _seed_operation_workflows(operation_approval_service: Any, *, reviewer_user_id: str) -> dict[str, Any]:
    step = {
        "step_name": "E2E审批",
        "members": [{"member_type": "user", "member_ref": reviewer_user_id}],
    }
    workflows = {}
    for operation_type, workflow_name in (
        ("knowledge_file_upload", "E2E文件上传审批流"),
        ("knowledge_file_delete", "E2E文件删除审批流"),
        ("knowledge_base_create", "E2E知识库创建审批流"),
        ("knowledge_base_delete", "E2E知识库删除审批流"),
    ):
        workflow = operation_approval_service.upsert_workflow(
            operation_type=operation_type,
            name=workflow_name,
            steps=[step],
        )
        workflows[operation_type] = {
            "name": str(workflow.get("name") or workflow_name),
            "step_count": len(workflow.get("steps") or []),
        }
    return workflows


def bootstrap_real_test_env(config: BootstrapConfig) -> dict[str, Any]:
    _assert_isolated_db_path(config.db_path)
    _reset_isolated_db_tree(config.db_path)

    global_db_path = ensure_database(db_path=str(config.db_path))
    global_deps = create_dependencies(db_path=str(global_db_path))
    admin_user = _ensure_admin_user(global_deps.user_store, username=config.admin_username, password=config.admin_password)

    org_summary = _rebuild_org(
        global_deps,
        actor_user_id=admin_user.user_id,
        excel_path=config.org_excel_path,
    )
    company = _select_company(global_deps, company_name=config.company_name, excel_path=config.org_excel_path)
    department = _select_department(
        global_deps,
        company_id=int(company.company_id),
        department_name=config.department_name,
    )
    if department is None:
        bootstrap_department_id = _ensure_bootstrap_department(
            db_path=Path(global_db_path),
            company_id=int(company.company_id),
            company_name=str(company.name),
        )
        department = global_deps.org_structure_manager.get_department(bootstrap_department_id)
        if department is None:
            raise RuntimeError(f"bootstrap_department_not_found:{bootstrap_department_id}")
    department_id = int(department.department_id)

    tenant_db_path = resolve_tenant_auth_db_path(company_id=int(company.company_id), base_db_path=global_db_path)
    tenant_deps = create_dependencies(
        db_path=str(tenant_db_path),
        operation_approval_control_db_path=str(global_db_path),
        training_compliance_db_path=str(global_db_path),
    )

    bootstrap_run_tag = _build_bootstrap_run_tag()
    dataset_name = _materialize_bootstrap_resource_name(
        _resolve_dataset_name(tenant_deps, config.dataset_name),
        explicit_name=config.dataset_name,
        env_var="E2E_REAL_DATASET_NAME",
        run_tag=bootstrap_run_tag,
    )
    chat_name = _materialize_bootstrap_resource_name(
        _resolve_chat_name(tenant_deps, config.chat_name),
        explicit_name=config.chat_name,
        env_var="E2E_REAL_CHAT_NAME",
        run_tag=bootstrap_run_tag,
    )
    managed_root_node_id = _ensure_managed_root_node(
        tenant_deps,
        root_name=config.managed_root_name,
        created_by=admin_user.user_id,
    )
    dataset_info = _ensure_dataset_binding(
        tenant_deps,
        node_id=managed_root_node_id,
        dataset_name=dataset_name,
    )
    if not _has_name_override(config.dataset_name, env_var="E2E_REAL_DATASET_NAME"):
        _unbind_previous_managed_dataset_bindings(
            tenant_deps,
            active_dataset_id=str(dataset_info.get("id") or ""),
        )
    chat_info = _ensure_chat_target(
        tenant_deps,
        chat_name=chat_name,
        dataset_info=dataset_info,
    )

    users_service = UsersService(UsersRepo(global_deps, permission_group_store=tenant_deps.permission_group_store))
    env_users = _build_users(config)
    _ensure_bootstrap_employee_profiles(
        db_path=Path(global_db_path),
        specs=list(env_users.values()),
        company_id=int(company.company_id),
        department_id=department_id,
    )

    sub_admin_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["sub_admin"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=None,
        managed_kb_root_node_id=managed_root_node_id,
        group_ids=None,
        assign_groups_after_create=False,
    )

    viewer_group_id = _ensure_owned_group(
        tenant_deps,
        owner_user_id=sub_admin_user.user_id,
        group_name=VIEWER_GROUP_NAME,
        description="E2E viewer scope",
        accessible_kb_nodes=[managed_root_node_id],
        can_upload=False,
        can_review=False,
        can_download=False,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
    )
    reviewer_group_id = _ensure_owned_group(
        tenant_deps,
        owner_user_id=sub_admin_user.user_id,
        group_name=REVIEWER_GROUP_NAME,
        description="E2E reviewer scope",
        accessible_kb_nodes=[managed_root_node_id],
        can_upload=False,
        can_review=True,
        can_download=True,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
    )
    uploader_group_id = _ensure_owned_group(
        tenant_deps,
        owner_user_id=sub_admin_user.user_id,
        group_name=UPLOADER_GROUP_NAME,
        description="E2E uploader scope",
        accessible_kb_nodes=[managed_root_node_id],
        can_upload=True,
        can_review=False,
        can_download=True,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
    )
    operator_group_id = _ensure_owned_group(
        tenant_deps,
        owner_user_id=sub_admin_user.user_id,
        group_name=OPERATOR_GROUP_NAME,
        description="E2E operator scope",
        accessible_kb_nodes=[managed_root_node_id],
        can_upload=True,
        can_review=True,
        can_download=True,
        can_copy=True,
        can_delete=True,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=True,
    )

    sub_admin_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["sub_admin"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=None,
        managed_kb_root_node_id=managed_root_node_id,
        group_ids=[operator_group_id],
        assign_groups_after_create=False,
    )
    operator_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["operator"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=sub_admin_user.user_id,
        managed_kb_root_node_id=None,
        group_ids=[operator_group_id],
        assign_groups_after_create=False,
    )
    reviewer_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["reviewer"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=sub_admin_user.user_id,
        managed_kb_root_node_id=None,
        group_ids=[reviewer_group_id],
        assign_groups_after_create=False,
    )
    uploader_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["uploader"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=sub_admin_user.user_id,
        managed_kb_root_node_id=None,
        group_ids=[uploader_group_id],
        assign_groups_after_create=True,
    )
    viewer_user = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=admin_user.user_id,
        spec=env_users["viewer"],
        company_id=int(company.company_id),
        department_id=department_id,
        manager_user_id=sub_admin_user.user_id,
        managed_kb_root_node_id=None,
        group_ids=[viewer_group_id],
        assign_groups_after_create=True,
    )

    training_service = tenant_deps.training_compliance_service
    reviewer_training = _seed_training_if_needed(
        training_service,
        user_id=reviewer_user.user_id,
        role_code=str(reviewer_user.role),
        controlled_action="document_review",
        actor_user_id=admin_user.user_id,
    )
    operator_training = _seed_training_if_needed(
        training_service,
        user_id=operator_user.user_id,
        role_code=str(operator_user.role),
        controlled_action="document_review",
        actor_user_id=admin_user.user_id,
    )
    admin_restore_training = _seed_training_if_needed(
        training_service,
        user_id=admin_user.user_id,
        role_code=str(admin_user.role),
        controlled_action="restore_drill_execute",
        actor_user_id=admin_user.user_id,
    )

    workflows = _seed_operation_workflows(
        tenant_deps.operation_approval_service,
        reviewer_user_id=reviewer_user.user_id,
    )

    return {
        "org": {
            "summary": org_summary,
            "company": {
                "id": int(company.company_id),
                "name": str(company.name),
            },
            "department": {
                "id": department_id,
                "name": (str(department.name) if department is not None else None),
                "path_name": (str(getattr(department, "path_name", "") or "") if department is not None else None),
            },
        },
        "knowledge": {
            "managed_root_node_id": managed_root_node_id,
            "managed_root_name": config.managed_root_name,
            "dataset": dataset_info,
            "chat": chat_info,
        },
        "groups": {
            "viewer": {"id": viewer_group_id, "name": VIEWER_GROUP_NAME},
            "reviewer": {"id": reviewer_group_id, "name": REVIEWER_GROUP_NAME},
            "uploader": {"id": uploader_group_id, "name": UPLOADER_GROUP_NAME},
            "operator": {"id": operator_group_id, "name": OPERATOR_GROUP_NAME},
        },
        "users": {
            "admin": {"username": admin_user.username, "user_id": admin_user.user_id, "role": admin_user.role},
            "sub_admin": {
                "username": sub_admin_user.username,
                "user_id": sub_admin_user.user_id,
                "role": sub_admin_user.role,
            },
            "operator": {
                "username": operator_user.username,
                "user_id": operator_user.user_id,
                "role": operator_user.role,
            },
            "viewer": {
                "username": viewer_user.username,
                "user_id": viewer_user.user_id,
                "role": viewer_user.role,
            },
            "reviewer": {
                "username": reviewer_user.username,
                "user_id": reviewer_user.user_id,
                "role": reviewer_user.role,
            },
            "uploader": {
                "username": uploader_user.username,
                "user_id": uploader_user.user_id,
                "role": uploader_user.role,
            },
        },
        "training": {
            "document_review": {
                "reviewer_allowed": bool(reviewer_training.get("allowed")),
                "operator_allowed": bool(operator_training.get("allowed")),
            },
            "restore_drill_execute": {
                "admin_allowed": bool(admin_restore_training.get("allowed")),
            },
        },
        "operation_workflows": workflows,
        "paths": {
            "global_db_path": str(Path(global_db_path).resolve()),
            "tenant_db_path": str(Path(tenant_db_path).resolve()),
            "org_excel_path": str(config.org_excel_path),
        },
    }


def parse_args(argv: list[str] | None = None) -> BootstrapConfig:
    parser = argparse.ArgumentParser(description="Bootstrap the real Playwright E2E environment.")
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--org-excel-path", default=None)
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--sub-admin-username", default="e2e_sub_admin")
    parser.add_argument("--sub-admin-password", default="admin123")
    parser.add_argument("--operator-username", default="e2e_operator")
    parser.add_argument("--operator-password", default="admin123")
    parser.add_argument("--viewer-username", default="e2e_viewer")
    parser.add_argument("--viewer-password", default="admin123")
    parser.add_argument("--reviewer-username", default="e2e_reviewer")
    parser.add_argument("--reviewer-password", default="admin123")
    parser.add_argument("--uploader-username", default="e2e_uploader")
    parser.add_argument("--uploader-password", default="admin123")
    parser.add_argument("--company-name", default=None)
    parser.add_argument("--department-name", default=None)
    parser.add_argument("--root-name", default=DEFAULT_MANAGED_ROOT_NAME)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--chat-name", default=None)
    parser.add_argument("--require-ragflow", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    db_path = resolve_auth_db_path(args.db_path) if args.db_path else resolve_auth_db_path()
    return BootstrapConfig(
        db_path=db_path,
        org_excel_path=_resolve_org_excel_path(args.org_excel_path),
        admin_username=_require_text("admin_username", args.admin_username),
        admin_password=_require_text("admin_password", args.admin_password),
        sub_admin_username=_require_text("sub_admin_username", args.sub_admin_username),
        sub_admin_password=_require_text("sub_admin_password", args.sub_admin_password),
        operator_username=_require_text("operator_username", args.operator_username),
        operator_password=_require_text("operator_password", args.operator_password),
        viewer_username=_require_text("viewer_username", args.viewer_username),
        viewer_password=_require_text("viewer_password", args.viewer_password),
        reviewer_username=_require_text("reviewer_username", args.reviewer_username),
        reviewer_password=_require_text("reviewer_password", args.reviewer_password),
        uploader_username=_require_text("uploader_username", args.uploader_username),
        uploader_password=_require_text("uploader_password", args.uploader_password),
        company_name=_optional_text(args.company_name),
        department_name=_optional_text(args.department_name),
        managed_root_name=_require_text("root_name", args.root_name),
        dataset_name=_optional_text(args.dataset_name),
        chat_name=_optional_text(args.chat_name),
        json_output=bool(args.json),
    )


def main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    try:
        summary = bootstrap_real_test_env(config)
    except Exception as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 1
    if config.json_output:
        print(json.dumps(summary, ensure_ascii=True))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
