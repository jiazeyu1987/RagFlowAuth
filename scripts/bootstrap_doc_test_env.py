#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.dependencies import create_dependencies
from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService
from backend.database.sqlite import connect_sqlite
from backend.services.electronic_signature.service import AuthorizedSignatureContext

from scripts.bootstrap_real_test_env import (
    EnvUserSpec,
    _build_dataset_create_payload,
    _ensure_bootstrap_employee_profile,
    _probe_ragflow_datasets,
    _upsert_user,
    bootstrap_real_test_env,
    parse_args as parse_base_args,
)


DOC_COMPANY_ADMIN_USERNAME = "doc_company_admin"
DOC_UNTRAINED_REVIEWER_USERNAME = "doc_untrained_reviewer"
DOC_NOTIFICATION_TARGET_USERNAME = "jiazeyu"
DOC_NOTIFICATION_TARGET_FULL_NAME = "贾泽宇"
DOC_LOGIN_USERNAME = "doc_login_user"
DOC_LOGIN_FULL_NAME = "Doc Login User"
DOC_TOOLS_EMPTY_USERNAME = "doc_tools_empty_user"
DOC_TOOLS_EMPTY_FULL_NAME = "Doc Tools Empty User"
DOC_USER_MANAGEMENT_USERNAME = "doc_user_management_user"
DOC_USER_MANAGEMENT_FULL_NAME = "Doc User Management User"
DOC_PASSWORD_CHANGE_USERNAME = "doc_password_change_user"
DOC_PASSWORD_CHANGE_FULL_NAME = "Doc Password Change User"
DOC_EMPTY_DATASET_BASE_NAME = "RagflowAuth Doc Empty Dataset"

GLOBAL_CLEAR_TABLES = (
    "operation_approval_events",
    "operation_approval_artifacts",
    "operation_approval_request_step_approvers",
    "operation_approval_request_steps",
    "operation_approval_requests",
    "operation_approval_legacy_migrations",
    "notification_delivery_logs",
    "notification_jobs",
)

TENANT_CLEAR_TABLES = (
    "notification_delivery_logs",
    "notification_jobs",
    "notification_event_rules",
    "notification_channels",
    "electronic_signature_challenges",
    "electronic_signatures",
    "deletion_logs",
    "download_logs",
    "kb_documents",
)


def _clear_tables(db_path: Path, table_names: tuple[str, ...]) -> None:
    conn = connect_sqlite(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for table_name in table_names:
            conn.execute(f"DELETE FROM {table_name}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _clear_training_for_users(db_path: Path, user_ids: list[str]) -> None:
    normalized_user_ids = [str(item).strip() for item in user_ids if str(item).strip()]
    if not normalized_user_ids:
        return
    placeholders = ",".join("?" for _ in normalized_user_ids)
    conn = connect_sqlite(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            f"DELETE FROM operator_certifications WHERE user_id IN ({placeholders})",
            normalized_user_ids,
        )
        conn.execute(
            f"DELETE FROM training_records WHERE user_id IN ({placeholders})",
            normalized_user_ids,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _write_fixture_file(*, repo_root: Path, relative_path: str, content: str) -> Path:
    output_path = repo_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8", newline="\n")
    return output_path


def _require_user(global_deps: Any, username: str):
    user = global_deps.user_store.get_by_username(username)
    if user is None:
        raise RuntimeError(f"user_not_found:{username}")
    return user


def _seed_signature(
    signature_service: Any,
    *,
    user: Any,
    record_type: str,
    record_id: str,
    action: str,
    meaning: str,
    reason: str,
    record_payload: dict[str, Any],
):
    now_ms = int(time.time() * 1000)
    signing_context = AuthorizedSignatureContext(
        token_id=f"doc-seed-{uuid4()}",
        user_id=str(user.user_id),
        consumed_at_ms=now_ms,
        expires_at_ms=now_ms + 60_000,
    )
    return signature_service.create_signature(
        signing_context=signing_context,
        user=user,
        record_type=record_type,
        record_id=record_id,
        action=action,
        meaning=meaning,
        reason=reason,
        record_payload=record_payload,
    )


def _seed_document_audit(tenant_deps: Any, *, repo_root: Path, company_admin: Any, reviewer_user: Any) -> dict[str, Any]:
    kb_store = tenant_deps.kb_store

    old_file = _write_fixture_file(
        repo_root=repo_root,
        relative_path="data/e2e/doc-fixtures/audit/quality-guide-v1.txt",
        content="Quality guide version 1\n",
    )
    new_file = _write_fixture_file(
        repo_root=repo_root,
        relative_path="data/e2e/doc-fixtures/audit/quality-guide-v2.txt",
        content="Quality guide version 2\n",
    )
    handbook_file = _write_fixture_file(
        repo_root=repo_root,
        relative_path="data/e2e/doc-fixtures/audit/compliance-handbook.txt",
        content="Compliance handbook\n",
    )

    old_doc = kb_store.create_document(
        filename="审计指南-v1.pdf",
        file_path=str(old_file),
        file_size=old_file.stat().st_size,
        mime_type="application/pdf",
        uploaded_by=str(company_admin.user_id),
        kb_id="KB-Alpha",
        kb_name="KB Alpha",
        status="approved",
        effective_status="approved",
    )
    old_doc = kb_store.update_document_status(
        doc_id=str(old_doc.doc_id),
        status="approved",
        reviewed_by=str(reviewer_user.user_id),
        review_notes="Doc E2E seeded version 1",
        ragflow_doc_id="doc-seed-audit-v1",
    )
    if old_doc is None:
        raise RuntimeError("doc_seed_old_update_failed")

    current_doc = kb_store.create_document(
        filename="审计指南-v2.pdf",
        file_path=str(new_file),
        file_size=new_file.stat().st_size,
        mime_type="application/pdf",
        uploaded_by=str(reviewer_user.user_id),
        kb_id="KB-Alpha",
        kb_name="KB Alpha",
        status="pending",
        effective_status="pending",
    )
    replacement_result = kb_store.apply_version_replacement(
        old_doc_id=str(old_doc.doc_id),
        new_doc_id=str(current_doc.doc_id),
        effective_status="pending",
    )
    if isinstance(replacement_result, dict):
        old_doc = replacement_result.get("old_doc") or replacement_result.get("old")
        current_doc = replacement_result.get("new_doc") or replacement_result.get("new")
    elif isinstance(replacement_result, (list, tuple)):
        if len(replacement_result) < 2:
            raise RuntimeError("doc_seed_version_replace_invalid_return")
        old_doc = replacement_result[0]
        current_doc = replacement_result[1]
    else:
        raise RuntimeError("doc_seed_version_replace_invalid_return")
    if old_doc is None or current_doc is None:
        raise RuntimeError("doc_seed_version_replace_failed")

    handbook_doc = kb_store.create_document(
        filename="合规手册.pdf",
        file_path=str(handbook_file),
        file_size=handbook_file.stat().st_size,
        mime_type="application/pdf",
        uploaded_by=str(company_admin.user_id),
        kb_id="KB-Beta",
        kb_name="KB Beta",
        status="approved",
        effective_status="approved",
    )
    handbook_doc = kb_store.update_document_status(
        doc_id=str(handbook_doc.doc_id),
        status="approved",
        reviewed_by=str(company_admin.user_id),
        review_notes="Doc E2E seeded handbook",
        ragflow_doc_id="doc-seed-handbook",
    )
    if handbook_doc is None:
        raise RuntimeError("doc_seed_handbook_update_failed")

    old_signature = _seed_signature(
        tenant_deps.electronic_signature_service,
        user=company_admin,
        record_type="knowledge_document_review",
        record_id=str(old_doc.doc_id),
        action="document_approve",
        meaning="Initial release",
        reason="Version 1 release approval",
        record_payload={
            "doc_id": str(old_doc.doc_id),
            "filename": str(old_doc.filename),
            "status": "approved",
        },
    )
    current_signature = _seed_signature(
        tenant_deps.electronic_signature_service,
        user=reviewer_user,
        record_type="knowledge_document_review",
        record_id=str(current_doc.doc_id),
        action="document_reject",
        meaning="Pending review",
        reason="Waiting for latest review decision",
        record_payload={
            "doc_id": str(current_doc.doc_id),
            "filename": str(current_doc.filename),
            "status": "pending",
        },
    )

    deletion_log = tenant_deps.deletion_log_store.log_deletion(
        doc_id="doc-deletion-1",
        filename="旧版政策.docx",
        kb_id="KB-Alpha",
        deleted_by=str(company_admin.user_id),
        kb_name="KB Alpha",
        original_uploader=str(company_admin.user_id),
        original_reviewer=str(reviewer_user.user_id),
        ragflow_doc_id="deleted-doc-1",
    )
    download_log_single = tenant_deps.download_log_store.log_download(
        doc_id=str(current_doc.doc_id),
        filename=str(current_doc.filename),
        kb_id="KB-Alpha",
        downloaded_by=str(reviewer_user.user_id),
        kb_name="KB Alpha",
        ragflow_doc_id="download-doc-1",
        is_batch=False,
    )
    download_log_batch = tenant_deps.download_log_store.log_download(
        doc_id=str(handbook_doc.doc_id),
        filename=str(handbook_doc.filename),
        kb_id="KB-Beta",
        downloaded_by=str(company_admin.user_id),
        kb_name="KB Beta",
        ragflow_doc_id="download-doc-2",
        is_batch=True,
    )

    return {
        "current_doc_id": str(current_doc.doc_id),
        "current_doc_filename": str(current_doc.filename),
        "previous_doc_id": str(old_doc.doc_id),
        "previous_doc_filename": str(old_doc.filename),
        "secondary_doc_id": str(handbook_doc.doc_id),
        "secondary_doc_filename": str(handbook_doc.filename),
        "kb_ids": ["KB-Alpha", "KB-Beta"],
        "version_signature_ids": {
            "previous": str(old_signature.signature_id),
            "current": str(current_signature.signature_id),
        },
        "deletion_log_id": int(deletion_log.id),
        "download_log_ids": {
            "single": int(download_log_single.id),
            "batch": int(download_log_batch.id),
        },
    }


def _import_approval_request(
    store: Any,
    *,
    request_id: str,
    applicant_user: Any,
    approver_user: Any,
    company_id: int,
    department_id: int | None,
    doc_id: str,
    filename: str,
    submitted_at_ms: int,
) -> dict[str, Any]:
    step_name = "文档审核"
    return store.import_request(
        request={
            "request_id": request_id,
            "operation_type": "legacy_document_review",
            "workflow_name": "历史文档审核",
            "status": "in_approval",
            "applicant_user_id": str(applicant_user.user_id),
            "applicant_username": str(applicant_user.username),
            "target_ref": str(doc_id),
            "target_label": str(filename),
            "summary": {
                "doc_id": str(doc_id),
                "filename": str(filename),
            },
            "payload": {
                "doc_id": str(doc_id),
                "filename": str(filename),
            },
            "result_payload": None,
            "workflow_snapshot": {
                "steps": [
                    {
                        "step_no": 1,
                        "step_name": step_name,
                        "approval_rule": "all",
                        "members": [
                            {
                                "member_type": "user",
                                "member_ref": str(approver_user.user_id),
                            }
                        ],
                    }
                ]
            },
            "current_step_no": 1,
            "current_step_name": step_name,
            "submitted_at_ms": int(submitted_at_ms),
            "completed_at_ms": None,
            "execution_started_at_ms": None,
            "executed_at_ms": None,
            "last_error": None,
            "company_id": int(company_id),
            "department_id": department_id,
        },
        steps=[
            {
                "step_no": 1,
                "step_name": step_name,
                "approval_rule": "all",
                "status": "active",
                "created_at_ms": int(submitted_at_ms),
                "activated_at_ms": int(submitted_at_ms),
                "completed_at_ms": None,
                "approvers": [
                    {
                        "approver_user_id": str(approver_user.user_id),
                        "approver_username": str(approver_user.username),
                        "status": "pending",
                        "action": None,
                        "notes": None,
                        "signature_id": None,
                        "acted_at_ms": None,
                    }
                ],
            }
        ],
        artifacts=[],
        events=[
            {
                "event_type": "request_submitted",
                "actor_user_id": str(applicant_user.user_id),
                "actor_username": str(applicant_user.username),
                "step_no": 1,
                "payload": {"target_label": str(filename)},
                "created_at_ms": int(submitted_at_ms),
            },
            {
                "event_type": "step_activated",
                "actor_user_id": str(applicant_user.user_id),
                "actor_username": str(applicant_user.username),
                "step_no": 1,
                "payload": {"current_step_name": step_name},
                "created_at_ms": int(submitted_at_ms),
            },
        ],
    )


def _seed_approval_requests(
    tenant_deps: Any,
    *,
    repo_root: Path,
    dataset_id: str,
    dataset_name: str,
    company_id: int,
    department_id: int | None,
    operator_user: Any,
    reviewer_user: Any,
    company_admin: Any,
    untrained_reviewer: Any,
) -> dict[str, Any]:
    kb_store = tenant_deps.kb_store
    approval_store = tenant_deps.operation_approval_service._store

    approval_docs: dict[str, Any] = {}
    for key, filename, content, applicant, approver in (
        ("approve", "审批通过样例.txt", "approval success fixture\n", operator_user, reviewer_user),
        ("reject", "审批驳回样例.txt", "approval reject fixture\n", operator_user, reviewer_user),
        ("withdraw", "我发起待撤回样例.txt", "approval withdraw fixture\n", reviewer_user, company_admin),
        ("training_missing", "培训门禁缺失样例.txt", "training missing fixture\n", operator_user, untrained_reviewer),
        ("training_expired", "培训失效拦截样例.txt", "training expired fixture\n", operator_user, untrained_reviewer),
    ):
        file_path = _write_fixture_file(
            repo_root=repo_root,
            relative_path=f"data/e2e/doc-fixtures/approval/{key}.txt",
            content=content,
        )
        doc = kb_store.create_document(
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type="text/plain; charset=utf-8",
            uploaded_by=str(applicant.user_id),
            kb_id=str(dataset_id),
            kb_dataset_id=str(dataset_id),
            kb_name=str(dataset_name),
            status="pending",
            effective_status="pending",
        )
        approval_docs[key] = {"doc": doc, "applicant": applicant, "approver": approver}

    base_ms = int(time.time() * 1000) - 300_000
    request_ids = {
        "approve": "doc-approval-center-approve",
        "reject": "doc-approval-center-reject",
        "withdraw": "doc-approval-center-withdraw",
        "training_missing": "doc-training-missing",
        "training_expired": "doc-training-expired",
    }

    for offset, key in enumerate(("approve", "reject", "withdraw", "training_missing", "training_expired"), start=1):
        item = approval_docs[key]
        _import_approval_request(
            approval_store,
            request_id=request_ids[key],
            applicant_user=item["applicant"],
            approver_user=item["approver"],
            company_id=company_id,
            department_id=department_id,
            doc_id=str(item["doc"].doc_id),
            filename=str(item["doc"].filename),
            submitted_at_ms=base_ms + (offset * 1_000),
        )

    operation_signature = _seed_signature(
        tenant_deps.electronic_signature_service,
        user=company_admin,
        record_type="operation_approval_request",
        record_id=request_ids["approve"],
        action="operation_approval_approve",
        meaning="Seeded signature detail",
        reason="Used by doc electronic signature management",
        record_payload={
            "request_id": request_ids["approve"],
            "status": "in_approval",
        },
    )

    return {
        "unit": {
            "approve_request_id": request_ids["approve"],
            "reject_request_id": request_ids["reject"],
            "withdraw_request_id": request_ids["withdraw"],
        },
        "training_gate": {
            "missing_request_id": request_ids["training_missing"],
            "expired_request_id": request_ids["training_expired"],
        },
        "signature_id": str(operation_signature.signature_id),
    }


def _seed_notifications(
    tenant_deps: Any,
    *,
    operator_user: Any,
    reviewer_user: Any,
    approval_requests: dict[str, Any],
    seed_configuration: bool = True,
) -> dict[str, Any]:
    manager = tenant_deps.notification_manager
    store = manager._store
    dedupe_suffix = uuid4().hex

    if seed_configuration:
        manager.upsert_channel(
            channel_id="email-main",
            channel_type="email",
            name="邮件通知",
            enabled=True,
            config={
                "host": "smtp.example.test",
                "port": 465,
                "username": "doc_notify",
                "password": "doc-password",
                "use_tls": True,
                "from_email": "doc@example.test",
            },
        )
        manager.upsert_channel(
            channel_id="dingtalk-main",
            channel_type="dingtalk",
            name="钉钉工作通知",
            enabled=True,
            config={
                "app_key": "doc-app-key",
                "app_secret": "doc-app-secret",
                "agent_id": "10001",
                "recipient_map": {
                    str(operator_user.user_id): "operator-ding-user",
                    str(operator_user.username): "operator-ding-user",
                    str(reviewer_user.user_id): "reviewer-ding-user",
                    str(reviewer_user.username): "reviewer-ding-user",
                },
                "api_base": "https://api.dingtalk.com",
                "oapi_base": "https://oapi.dingtalk.com",
                "timeout_seconds": 30,
            },
        )
        manager.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="站内信",
            enabled=True,
            config={},
        )
        manager.upsert_event_rules(
            items=[
                {
                    "event_type": "operation_approval_todo",
                    "enabled_channel_types": ["email", "in_app"],
                },
                {
                    "event_type": "review_todo_approval",
                    "enabled_channel_types": ["in_app"],
                },
            ]
        )
    else:
        existing_channel = store.get_channel("inapp-main")
        if existing_channel is None or not bool(existing_channel.get("enabled")):
            manager.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="站内信",
                enabled=True,
                config={},
            )

    history_payload_base = {
        "link_path": f"/approvals?request_id={approval_requests['unit']['approve_request_id']}",
        "title": "审批待处理通知",
        "body": "审批中心文档 E2E 历史记录",
    }
    queued_job = store.create_job(
        channel_id="inapp-main",
        event_type="operation_approval_todo",
        payload={**history_payload_base, "job_kind": "queued"},
        recipient_user_id=str(reviewer_user.user_id),
        recipient_username=str(reviewer_user.username),
        recipient_address=str(reviewer_user.user_id),
        dedupe_key=f"doc-history-queued-{dedupe_suffix}",
        max_attempts=3,
    )
    store.add_delivery_log(job_id=int(queued_job["job_id"]), channel_id="inapp-main", status="queued")

    sent_job = store.create_job(
        channel_id="inapp-main",
        event_type="operation_approval_todo",
        payload={**history_payload_base, "job_kind": "sent"},
        recipient_user_id=str(reviewer_user.user_id),
        recipient_username=str(reviewer_user.username),
        recipient_address=str(reviewer_user.user_id),
        dedupe_key=f"doc-history-sent-{dedupe_suffix}",
        max_attempts=3,
    )
    store.add_delivery_log(job_id=int(sent_job["job_id"]), channel_id="inapp-main", status="queued")
    sent_job = store.mark_job_sent(job_id=int(sent_job["job_id"]))
    store.add_delivery_log(job_id=int(sent_job["job_id"]), channel_id="inapp-main", status="sent")

    failed_job = store.create_job(
        channel_id="inapp-main",
        event_type="review_todo_approval",
        payload={
            "title": "审核失败通知",
            "body": "用于真实重试场景",
            "link_path": f"/approvals?request_id={approval_requests['unit']['reject_request_id']}",
        },
        recipient_user_id=str(operator_user.user_id),
        recipient_username=str(operator_user.username),
        recipient_address=str(operator_user.user_id),
        dedupe_key=f"doc-history-failed-{dedupe_suffix}",
        max_attempts=1,
    )
    store.add_delivery_log(job_id=int(failed_job["job_id"]), channel_id="inapp-main", status="queued")
    failed_job = store.mark_job_failed(
        job_id=int(failed_job["job_id"]),
        error="seeded_delivery_failure",
        retry_interval_seconds=60,
    )
    store.add_delivery_log(
        job_id=int(failed_job["job_id"]),
        channel_id="inapp-main",
        status="failed",
        error="seeded_delivery_failure",
    )

    inbox_unread = store.create_job(
        channel_id="inapp-main",
        event_type="operation_approval_todo",
        payload={
            "title": "文档待审核",
            "body": "点击后进入审批详情",
            "link_path": f"/approvals?request_id={approval_requests['unit']['approve_request_id']}",
            "request_id": approval_requests["unit"]["approve_request_id"],
        },
        recipient_user_id=str(operator_user.user_id),
        recipient_username=str(operator_user.username),
        recipient_address=str(operator_user.user_id),
        dedupe_key=f"doc-inbox-unread-1-{dedupe_suffix}",
        max_attempts=3,
    )
    store.add_delivery_log(job_id=int(inbox_unread["job_id"]), channel_id="inapp-main", status="queued")
    inbox_unread = store.mark_job_sent(job_id=int(inbox_unread["job_id"]))
    store.add_delivery_log(job_id=int(inbox_unread["job_id"]), channel_id="inapp-main", status="sent")

    inbox_read = store.create_job(
        channel_id="inapp-main",
        event_type="review_todo_approval",
        payload={
            "title": "审核已完成",
            "body": "已读站内信样例",
            "link_path": f"/approvals?request_id={approval_requests['unit']['reject_request_id']}",
            "request_id": approval_requests["unit"]["reject_request_id"],
        },
        recipient_user_id=str(operator_user.user_id),
        recipient_username=str(operator_user.username),
        recipient_address=str(operator_user.user_id),
        dedupe_key=f"doc-inbox-read-1-{dedupe_suffix}",
        max_attempts=3,
    )
    store.add_delivery_log(job_id=int(inbox_read["job_id"]), channel_id="inapp-main", status="queued")
    inbox_read = store.mark_job_sent(job_id=int(inbox_read["job_id"]))
    store.add_delivery_log(job_id=int(inbox_read["job_id"]), channel_id="inapp-main", status="sent")
    store.set_inbox_read_state(
        job_id=int(inbox_read["job_id"]),
        recipient_user_id=str(operator_user.user_id),
        read=True,
    )

    inbox_unread_2 = store.create_job(
        channel_id="inapp-main",
        event_type="operation_approval_todo",
        payload={
            "title": "合规提醒",
            "body": "第二条未读消息样例",
            "link_path": f"/approvals?request_id={approval_requests['unit']['withdraw_request_id']}",
            "request_id": approval_requests["unit"]["withdraw_request_id"],
        },
        recipient_user_id=str(operator_user.user_id),
        recipient_username=str(operator_user.username),
        recipient_address=str(operator_user.user_id),
        dedupe_key=f"doc-inbox-unread-2-{dedupe_suffix}",
        max_attempts=3,
    )
    store.add_delivery_log(job_id=int(inbox_unread_2["job_id"]), channel_id="inapp-main", status="queued")
    inbox_unread_2 = store.mark_job_sent(job_id=int(inbox_unread_2["job_id"]))
    store.add_delivery_log(job_id=int(inbox_unread_2["job_id"]), channel_id="inapp-main", status="sent")

    return {
        "history": {
            "queued_job_id": int(queued_job["job_id"]),
            "sent_job_id": int(sent_job["job_id"]),
            "failed_job_id": int(failed_job["job_id"]),
        },
        "inbox": {
            "unread_job_ids": [int(inbox_unread["job_id"]), int(inbox_unread_2["job_id"])],
            "read_job_id": int(inbox_read["job_id"]),
        },
    }


def _ensure_empty_dataset_fixture(tenant_deps: Any, *, node_id: str) -> dict[str, str]:
    clean_node_id = str(node_id or "").strip()
    if not clean_node_id:
        raise RuntimeError("doc_empty_dataset_node_required")

    dataset_name = f"{DOC_EMPTY_DATASET_BASE_NAME} [{uuid4().hex[:8]}]"
    datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
    payload = _build_dataset_create_payload(existing_datasets=datasets, dataset_name=dataset_name)
    try:
        created = tenant_deps.ragflow_service.create_dataset(payload)
    except Exception as exc:
        raise RuntimeError(f"doc_empty_dataset_create_failed:{dataset_name}; {exc}") from exc

    dataset = created if isinstance(created, dict) else None
    if dataset is None:
        datasets = _probe_ragflow_datasets(tenant_deps.ragflow_service)
        dataset = next((item for item in datasets if str(item.get("name") or "").strip() == dataset_name), None)
    if dataset is None:
        raise RuntimeError(f"doc_empty_dataset_missing:{dataset_name}")

    dataset_id = str(dataset.get("id") or "").strip()
    resolved_name = str(dataset.get("name") or dataset_name).strip() or dataset_name
    if not dataset_id:
        raise RuntimeError(f"doc_empty_dataset_missing_id:{dataset_name}")

    tenant_deps.knowledge_directory_store.assign_dataset(dataset_id, clean_node_id)
    documents = [
        item
        for item in tenant_deps.ragflow_service.list_documents(dataset_id)
        if isinstance(item, dict)
    ]
    if documents:
        raise RuntimeError(f"doc_empty_dataset_not_empty:{resolved_name}")

    return {
        "id": dataset_id,
        "name": resolved_name,
        "node_id": clean_node_id,
    }


def bootstrap_doc_test_env(config) -> dict[str, Any]:
    base_summary = bootstrap_real_test_env(config)
    global_db_path = Path(base_summary["paths"]["global_db_path"]).resolve()
    tenant_db_path = Path(base_summary["paths"]["tenant_db_path"]).resolve()

    _clear_tables(global_db_path, GLOBAL_CLEAR_TABLES)
    _clear_tables(tenant_db_path, TENANT_CLEAR_TABLES)

    global_deps = create_dependencies(db_path=str(global_db_path))
    tenant_deps = create_dependencies(
        db_path=str(tenant_db_path),
        operation_approval_control_db_path=str(global_db_path),
        training_compliance_db_path=str(global_db_path),
    )
    users_service = UsersService(UsersRepo(global_deps, permission_group_store=tenant_deps.permission_group_store))

    base_users = base_summary["users"]
    company_id = int(base_summary["org"]["company"]["id"])
    department_id = base_summary["org"]["department"]["id"]
    if department_id is None:
        raise RuntimeError("doc_bootstrap_department_required")
    department_id = int(department_id)
    reviewer_group_id = int(base_summary["groups"]["reviewer"]["id"])
    operator_user = _require_user(global_deps, base_users["operator"]["username"])
    reviewer_user = _require_user(global_deps, base_users["reviewer"]["username"])
    viewer_user = _require_user(global_deps, base_users["viewer"]["username"])
    sub_admin_user = _require_user(global_deps, base_users["sub_admin"]["username"])
    admin_user = _require_user(global_deps, base_users["admin"]["username"])

    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_COMPANY_ADMIN_USERNAME,
        full_name="Doc Company Admin",
        email=f"{DOC_COMPANY_ADMIN_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_UNTRAINED_REVIEWER_USERNAME,
        full_name="Doc Untrained Reviewer",
        email=f"{DOC_UNTRAINED_REVIEWER_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_NOTIFICATION_TARGET_USERNAME,
        full_name=DOC_NOTIFICATION_TARGET_FULL_NAME,
        email=f"{DOC_NOTIFICATION_TARGET_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_LOGIN_USERNAME,
        full_name=DOC_LOGIN_FULL_NAME,
        email=f"{DOC_LOGIN_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_TOOLS_EMPTY_USERNAME,
        full_name=DOC_TOOLS_EMPTY_FULL_NAME,
        email=f"{DOC_TOOLS_EMPTY_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_USER_MANAGEMENT_USERNAME,
        full_name=DOC_USER_MANAGEMENT_FULL_NAME,
        email=f"{DOC_USER_MANAGEMENT_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )
    _ensure_bootstrap_employee_profile(
        db_path=global_db_path,
        employee_user_id=DOC_PASSWORD_CHANGE_USERNAME,
        full_name=DOC_PASSWORD_CHANGE_FULL_NAME,
        email=f"{DOC_PASSWORD_CHANGE_USERNAME}@example.test",
        company_id=company_id,
        department_id=department_id,
    )

    company_admin = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=str(admin_user.user_id),
        spec=EnvUserSpec(
            username=DOC_COMPANY_ADMIN_USERNAME,
            full_name="Doc Company Admin",
            email=f"{DOC_COMPANY_ADMIN_USERNAME}@example.test",
            role="admin",
            password=config.admin_password,
        ),
        company_id=company_id,
        department_id=department_id,
        manager_user_id=None,
        managed_kb_root_node_id=None,
        group_ids=None,
        assign_groups_after_create=False,
    )
    untrained_reviewer = _upsert_user(
        users_service=users_service,
        user_store=global_deps.user_store,
        created_by=str(admin_user.user_id),
        spec=EnvUserSpec(
            username=DOC_UNTRAINED_REVIEWER_USERNAME,
            full_name="Doc Untrained Reviewer",
            email=f"{DOC_UNTRAINED_REVIEWER_USERNAME}@example.test",
            role="reviewer",
            password=config.admin_password,
        ),
        company_id=company_id,
        department_id=department_id,
        manager_user_id=str(sub_admin_user.user_id),
        managed_kb_root_node_id=None,
        group_ids=[reviewer_group_id],
        assign_groups_after_create=False,
    )

    _clear_training_for_users(
        global_db_path,
        [str(untrained_reviewer.user_id), str(viewer_user.user_id)],
    )

    requirement = None
    for item in tenant_deps.training_compliance_service.list_requirements(
        limit=100,
        controlled_action="document_review",
    ):
        requirement = item
        break
    if requirement is None:
        raise RuntimeError("doc_training_requirement_not_found")

    document_fixtures = _seed_document_audit(
        tenant_deps,
        repo_root=REPO_ROOT,
        company_admin=company_admin,
        reviewer_user=reviewer_user,
    )
    approval_fixtures = _seed_approval_requests(
        tenant_deps,
        repo_root=REPO_ROOT,
        dataset_id=str(base_summary["knowledge"]["dataset"]["id"]),
        dataset_name=str(base_summary["knowledge"]["dataset"]["name"]),
        company_id=company_id,
        department_id=department_id,
        operator_user=operator_user,
        reviewer_user=reviewer_user,
        company_admin=company_admin,
        untrained_reviewer=untrained_reviewer,
    )
    tenant_notification_fixtures = _seed_notifications(
        tenant_deps,
        operator_user=operator_user,
        reviewer_user=reviewer_user,
        approval_requests=approval_fixtures,
    )
    global_notification_fixtures = _seed_notifications(
        global_deps,
        operator_user=operator_user,
        reviewer_user=reviewer_user,
        approval_requests=approval_fixtures,
        seed_configuration=False,
    )
    empty_dataset_fixture = _ensure_empty_dataset_fixture(
        tenant_deps,
        node_id=str(base_summary["knowledge"]["managed_root_node_id"]),
    )

    summary = dict(base_summary)
    summary["knowledge"] = {
        **base_summary["knowledge"],
        "empty_dataset": empty_dataset_fixture,
    }
    summary["users"] = {
        **base_summary["users"],
        "company_admin": {
            "username": str(company_admin.username),
            "user_id": str(company_admin.user_id),
            "role": str(company_admin.role),
        },
        "untrained_reviewer": {
            "username": str(untrained_reviewer.username),
            "user_id": str(untrained_reviewer.user_id),
            "role": str(untrained_reviewer.role),
        },
        "user_management_target": {
            "username": DOC_USER_MANAGEMENT_USERNAME,
            "full_name": DOC_USER_MANAGEMENT_FULL_NAME,
        },
        "password_change_target": {
            "username": DOC_PASSWORD_CHANGE_USERNAME,
            "full_name": DOC_PASSWORD_CHANGE_FULL_NAME,
        },
    }
    summary["doc_fixtures"] = {
        "training": {
            "requirement_code": str(requirement["requirement_code"]),
            "curriculum_version": str(requirement["curriculum_version"]),
            "controlled_action": str(requirement["controlled_action"]),
            "unit_target_user_id": str(viewer_user.user_id),
            "unit_target_username": str(viewer_user.username),
            "role_target_user_id": str(untrained_reviewer.user_id),
            "role_target_username": str(untrained_reviewer.username),
        },
        "documents": document_fixtures,
        "approvals": approval_fixtures,
        "notifications": {
            "history": dict(global_notification_fixtures.get("history") or {}),
            "inbox": dict(tenant_notification_fixtures.get("inbox") or {}),
        },
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    config = parse_base_args(argv)
    try:
        summary = bootstrap_doc_test_env(config)
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
