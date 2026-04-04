import asyncio
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.core.config import settings
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.inbox_service import UserInboxService
from backend.services.inbox_store import UserInboxStore
from backend.services.kb import KbStore
from backend.services.notification import NotificationService, NotificationStore
from backend.services.operation_approval import (
    OperationApprovalService,
    OperationApprovalServiceError,
    OperationApprovalStore,
)
from backend.services.users import hash_password
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class _UploadFileStub:
    def __init__(self, filename: str, content: bytes, content_type: str = "text/plain"):
        self.filename = filename
        self.content_type = content_type
        self._content = bytes(content)

    async def read(self):
        return self._content


class _OrgDirectoryStore:
    def get_company(self, company_id: int):
        return SimpleNamespace(name=f"Company-{company_id}")

    def get_department(self, department_id: int):
        return SimpleNamespace(name=f"Department-{department_id}")


class _UserStore:
    def __init__(self, users: list[SimpleNamespace]):
        self._users = {str(user.user_id): user for user in users}

    def get_by_user_id(self, user_id: str):
        return self._users.get(str(user_id))


class _DeletionLogStore:
    def __init__(self):
        self.calls: list[dict] = []

    def log_deletion(self, **kwargs):
        self.calls.append(kwargs)


class _NoopAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class _FakeRagflowService:
    def __init__(self):
        self.datasets: dict[str, dict] = {}
        self.deleted_documents: list[tuple[str, str | None]] = []
        self.created_payloads: list[dict] = []
        self.deleted_dataset_refs: list[str] = []
        self.uploaded_documents: list[dict] = []
        self.parsed_documents: list[dict] = []
        self._counter = 1
        self._uploaded_counter = 1

    def add_dataset(
        self,
        *,
        dataset_id: str,
        name: str,
        document_count: int = 0,
        chunk_count: int = 0,
    ) -> None:
        self.datasets[str(dataset_id)] = {
            "id": str(dataset_id),
            "name": str(name),
            "document_count": int(document_count),
            "chunk_count": int(chunk_count),
        }

    def _find_dataset(self, dataset_ref: str) -> dict | None:
        clean_ref = str(dataset_ref or "").strip()
        if clean_ref in self.datasets:
            return self.datasets[clean_ref]
        for item in self.datasets.values():
            if str(item.get("name") or "") == clean_ref:
                return item
        return None

    def normalize_dataset_id(self, dataset_ref: str) -> str | None:
        item = self._find_dataset(dataset_ref)
        return str(item["id"]) if item else None

    def resolve_dataset_name(self, dataset_ref: str) -> str | None:
        item = self._find_dataset(dataset_ref)
        return str(item["name"]) if item else None

    def get_dataset_detail(self, dataset_ref: str) -> dict | None:
        item = self._find_dataset(dataset_ref)
        return dict(item) if item else None

    def create_dataset(self, payload: dict) -> dict:
        name = str((payload or {}).get("name") or "").strip()
        if not name:
            raise RuntimeError("missing_name")
        for item in self.datasets.values():
            if str(item.get("name") or "") == name:
                raise RuntimeError("dataset_name_conflict")
        dataset_id = f"ds-created-{self._counter}"
        self._counter += 1
        created = {
            "id": dataset_id,
            "name": name,
            "document_count": 0,
            "chunk_count": 0,
        }
        self.datasets[dataset_id] = created
        self.created_payloads.append(dict(payload or {}))
        return dict(created)

    def delete_dataset_if_empty(self, dataset_ref: str) -> None:
        item = self._find_dataset(dataset_ref)
        if not item:
            raise ValueError("dataset_not_found")
        if int(item.get("document_count") or 0) > 0 or int(item.get("chunk_count") or 0) > 0:
            raise ValueError("dataset_not_empty")
        self.deleted_dataset_refs.append(str(item["id"]))
        del self.datasets[str(item["id"])]

    def delete_document(self, ragflow_doc_id: str, dataset_name: str | None = None) -> bool:
        self.deleted_documents.append((str(ragflow_doc_id), dataset_name))
        return True

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "展厅") -> str:
        doc_id = f"rag-doc-{self._uploaded_counter}"
        self._uploaded_counter += 1
        self.uploaded_documents.append(
            {
                "doc_id": doc_id,
                "file_filename": str(file_filename),
                "file_content": bytes(file_content),
                "kb_id": str(kb_id),
            }
        )
        return doc_id

    def parse_document(self, *, dataset_ref: str, document_id: str) -> bool:
        self.parsed_documents.append({"dataset_ref": str(dataset_ref), "document_id": str(document_id)})
        return True


class _KnowledgeManagementManager:
    def __init__(self, ragflow_service: _FakeRagflowService):
        self._ragflow_service = ragflow_service
        self.prepare_create_calls: list[dict] = []
        self.create_calls: list[dict] = []
        self.prepare_delete_calls: list[str] = []
        self.delete_calls: list[str] = []

    def prepare_dataset_create_payload(self, *, user, payload: dict):  # noqa: ARG002
        self.prepare_create_calls.append(dict(payload or {}))
        body = dict(payload or {})
        name = str(body.get("name") or "").strip()
        if not name:
            raise ValueError("missing_name")
        body["name"] = name
        body.pop("id", None)
        body.pop("dataset_id", None)
        return body

    def create_dataset(self, *, user, payload: dict):  # noqa: ARG002
        self.create_calls.append(dict(payload or {}))
        return self._ragflow_service.create_dataset(payload)

    def prepare_dataset_delete(self, *, user, dataset_ref: str):  # noqa: ARG002
        self.prepare_delete_calls.append(str(dataset_ref))
        detail = self._ragflow_service.get_dataset_detail(dataset_ref)
        if not detail:
            raise ValueError("dataset_not_found")
        if int(detail.get("document_count") or 0) > 0 or int(detail.get("chunk_count") or 0) > 0:
            raise ValueError("dataset_not_empty")
        return {
            "dataset_ref": str(dataset_ref),
            "dataset_id": str(detail.get("id") or dataset_ref),
            "dataset_name": str(detail.get("name") or dataset_ref),
        }

    def delete_dataset(self, *, user, dataset_ref: str):  # noqa: ARG002
        self.delete_calls.append(str(dataset_ref))
        return self._ragflow_service.delete_dataset_if_empty(dataset_ref)


def _make_user(
    user_id: str,
    *,
    role: str = "viewer",
    status: str = "active",
    email: str | None = None,
    company_id: int = 1,
    department_id: int = 10,
    manager_user_id: str | None = None,
):
    username = user_id.replace("-", "_")
    return SimpleNamespace(
        user_id=user_id,
        username=username,
        full_name=username.title(),
        email=email or f"{username}@example.com",
        role=role,
        status=status,
        company_id=company_id,
        department_id=department_id,
        manager_user_id=manager_user_id,
        group_ids=[],
        password_hash=hash_password(SIGN_PASSWORD),
    )


def _snapshot(
    *,
    is_admin: bool = False,
    can_upload: bool = False,
    can_delete: bool = False,
    kb_names: tuple[str, ...] = (),
) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=is_admin,
        can_upload=can_upload,
        can_review=False,
        can_download=False,
        can_copy=False,
        can_delete=can_delete,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
        kb_scope=(ResourceScope.SET if kb_names else ResourceScope.NONE),
        kb_names=frozenset(kb_names),
        chat_scope=ResourceScope.NONE,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.NONE,
        tool_ids=frozenset(),
    )


class TestOperationApprovalServiceUnit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = make_temp_dir(prefix="ragflowauth_operation_approval")
        self.db_path = os.path.join(str(self.temp_dir), "auth.db")
        ensure_schema(self.db_path)

        self.upload_root = Path(self.temp_dir) / "uploads"
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.upload_dir_patcher = patch.object(settings, "UPLOAD_DIR", str(self.upload_root))
        self.upload_dir_patcher.start()

        self.admin_user = _make_user("admin-1", role="admin")
        self.editor_user = _make_user("editor-1", role="editor")
        self.approver_1 = _make_user("approver-1", role="reviewer")
        self.approver_2 = _make_user("approver-2", role="reviewer")
        self.approver_3 = _make_user("approver-3", role="reviewer")
        self.outsider_user = _make_user("outsider-1", role="reviewer")
        self.inactive_user = _make_user("inactive-1", role="reviewer", status="inactive")

        self.user_store = _UserStore(
            [
                self.admin_user,
                self.editor_user,
                self.approver_1,
                self.approver_2,
                self.approver_3,
                self.outsider_user,
                self.inactive_user,
            ]
        )
        self.kb_store = KbStore(db_path=self.db_path)
        self.audit_store = AuditLogStore(db_path=self.db_path)
        self.signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=self.db_path))
        self.inbox_service = UserInboxService(store=UserInboxStore(db_path=self.db_path))
        self.notification_store = NotificationStore(db_path=self.db_path)
        self.notification_service = NotificationService(
            store=self.notification_store,
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        self.notification_service.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="In App",
            enabled=True,
            config={},
        )
        self.notification_service.upsert_channel(
            channel_id="email-main",
            channel_type="email",
            name="Main Email",
            enabled=True,
            config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
        )
        self.ragflow_service = _FakeRagflowService()
        self.knowledge_management_manager = _KnowledgeManagementManager(self.ragflow_service)
        self.deletion_log_store = _DeletionLogStore()
        self.org_directory_store = _OrgDirectoryStore()
        self.org_structure_manager = self.org_directory_store

        self.deps = SimpleNamespace(
            kb_store=self.kb_store,
            audit_log_store=self.audit_store,
            org_directory_store=self.org_directory_store,
            org_structure_manager=self.org_structure_manager,
            notification_service=self.notification_service,
            deletion_log_store=self.deletion_log_store,
            ragflow_service=self.ragflow_service,
            knowledge_management_manager=self.knowledge_management_manager,
            upload_settings_store=None,
        )
        self.service = OperationApprovalService(
            store=OperationApprovalStore(db_path=self.db_path),
            user_store=self.user_store,
            inbox_service=self.inbox_service,
            notification_service=self.notification_service,
            electronic_signature_service=self.signature_service,
            deps=self.deps,
        )
        self.deps.operation_approval_service = self.service

    def tearDown(self):
        self.upload_dir_patcher.stop()
        cleanup_dir(self.temp_dir)

    def _ctx(self, user: SimpleNamespace, snapshot: PermissionSnapshot):
        return SimpleNamespace(
            deps=self.deps,
            user=user,
            payload=SimpleNamespace(sub=str(user.user_id)),
            snapshot=snapshot,
        )

    def _issue_sign_token(self, user: SimpleNamespace) -> str:
        challenge = self.signature_service.issue_challenge(user=user, password=SIGN_PASSWORD)
        return str(challenge["sign_token"])

    def _upsert_workflow(self, operation_type: str, steps: list[dict]):
        return self.service.upsert_workflow(
            operation_type=operation_type,
            name=None,
            steps=steps,
        )

    def _upsert_workflow_members(self, operation_type: str, steps: list[dict]):
        return self.service.upsert_workflow(
            operation_type=operation_type,
            name=None,
            steps=steps,
        )

    def _create_dataset_request(self, name: str = "New Dataset", *, applicant: SimpleNamespace | None = None):
        applicant = applicant or self.admin_user
        return asyncio.run(
            self.service.create_request(
                operation_type="knowledge_base_create",
                ctx=self._ctx(applicant, _snapshot(is_admin=True)),
                body={"name": name},
            )
        )

    def _create_delete_dataset_request(self, dataset_ref: str, *, applicant: SimpleNamespace | None = None):
        applicant = applicant or self.admin_user
        return asyncio.run(
            self.service.create_request(
                operation_type="knowledge_base_delete",
                ctx=self._ctx(applicant, _snapshot(is_admin=True)),
                dataset_ref=dataset_ref,
            )
        )

    def _create_upload_request(self, *, filename: str = "upload.txt", kb_ref: str = "kb-a", content: bytes = b"hello"):
        return asyncio.run(
            self.service.create_request(
                operation_type="knowledge_file_upload",
                ctx=self._ctx(self.editor_user, _snapshot(can_upload=True, kb_names=(kb_ref, "ds-kb-a"))),
                upload_file=_UploadFileStub(filename=filename, content=content),
                kb_ref=kb_ref,
            )
        )

    def _create_delete_document_request(self, doc_id: str):
        return asyncio.run(
            self.service.create_request(
                operation_type="knowledge_file_delete",
                ctx=self._ctx(self.editor_user, _snapshot(can_delete=True, kb_names=("kb-a", "ds-kb-a"))),
                doc_id=doc_id,
            )
        )

    def _approve(self, request_id: str, actor_user: SimpleNamespace, *, notes: str | None = None):
        return self.service.approve_request(
            request_id=request_id,
            actor_user=actor_user,
            sign_token=self._issue_sign_token(actor_user),
            signature_meaning="Approval",
            signature_reason="Approve request",
            notes=notes,
        )

    def _reject(self, request_id: str, actor_user: SimpleNamespace, *, notes: str | None = None):
        return self.service.reject_request(
            request_id=request_id,
            actor_user=actor_user,
            sign_token=self._issue_sign_token(actor_user),
            signature_meaning="Rejection",
            signature_reason="Reject request",
            notes=notes,
        )

    def _seed_document(self, *, filename: str = "seed.txt", content: bytes = b"seed", ragflow_doc_id: str | None = None):
        file_path = Path(self.temp_dir) / filename
        file_path.write_bytes(content)
        doc = self.kb_store.create_document(
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type="text/plain",
            uploaded_by=str(self.editor_user.user_id),
            kb_id="kb-a",
            kb_dataset_id="ds-kb-a",
            kb_name="kb-a",
            status="approved",
        )
        if ragflow_doc_id:
            self.kb_store.update_document_status(doc_id=doc.doc_id, status="approved", ragflow_doc_id=ragflow_doc_id)
            doc = self.kb_store.get_document(doc.doc_id)
        return doc

    def test_upsert_workflow_validates_steps_and_active_users(self):
        with self.assertRaises(OperationApprovalServiceError) as empty_ctx:
            self.service.upsert_workflow(operation_type="knowledge_base_create", name=None, steps=[])
        self.assertEqual(empty_ctx.exception.code, "workflow_steps_required")

        with self.assertRaises(OperationApprovalServiceError) as invalid_member_ctx:
            self.service.upsert_workflow(
                operation_type="knowledge_base_create",
                name=None,
                steps=[
                    {
                        "step_name": "Step 1",
                        "members": [{"member_type": "unknown", "member_ref": "x"}],
                    }
                ],
            )
        self.assertEqual(invalid_member_ctx.exception.code, "workflow_step_member_type_invalid")

        with self.assertRaises(OperationApprovalServiceError) as inactive_ctx:
            self.service.upsert_workflow(
                operation_type="knowledge_base_create",
                name=None,
                steps=[
                    {
                        "step_name": "Step 1",
                        "members": [{"member_type": "user", "member_ref": self.inactive_user.user_id}],
                    }
                ],
            )
        self.assertEqual(inactive_ctx.exception.code, "workflow_approver_inactive")

    def test_request_snapshot_isolated_from_later_workflow_changes(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Manager Review", "approver_user_ids": [self.approver_1.user_id]}],
        )
        first = self._create_dataset_request(name="Dataset Snapshot A")

        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Director Review", "approver_user_ids": [self.approver_2.user_id]}],
        )
        second = self._create_dataset_request(name="Dataset Snapshot B")

        first_detail = self.service.get_request_detail_for_user(
            request_id=first["request_id"],
            requester_user=self.admin_user,
        )
        second_detail = self.service.get_request_detail_for_user(
            request_id=second["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(first_detail["steps"][0]["step_name"], "Manager Review")
        self.assertEqual(first_detail["steps"][0]["approvers"][0]["approver_user_id"], self.approver_1.user_id)
        self.assertEqual(second_detail["steps"][0]["step_name"], "Director Review")
        self.assertEqual(second_detail["steps"][0]["approvers"][0]["approver_user_id"], self.approver_2.user_id)

    def test_request_detail_exposes_approver_full_name(self):
        self.admin_user.full_name = "Applicant User"
        self.approver_1.full_name = "王歆"
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Manager Review", "approver_user_ids": [self.approver_1.user_id]}],
        )

        request = self._create_dataset_request(name="Dataset Full Name")
        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )
        self.assertEqual(detail["applicant_username"], self.admin_user.username)
        self.assertEqual(detail["applicant_full_name"], "Applicant User")

        self.assertEqual(detail["steps"][0]["approvers"][0]["approver_username"], self.approver_1.username)
        self.assertEqual(detail["events"][0]["actor_username"], self.admin_user.username)
        self.assertEqual(detail["events"][0]["actor_full_name"], "Applicant User")
        self.assertEqual(detail["steps"][0]["approvers"][0]["approver_full_name"], "王歆")

    def test_direct_manager_resolves_at_submission_and_snapshot_keeps_member_definition(self):
        self.admin_user.manager_user_id = self.approver_1.user_id
        self._upsert_workflow_members(
            "knowledge_base_create",
            [
                {
                    "step_name": "Manager Review",
                    "members": [{"member_type": "special_role", "member_ref": "direct_manager"}],
                }
            ],
        )

        request = self._create_dataset_request(name="Dataset Direct Manager")
        self.admin_user.manager_user_id = self.approver_2.user_id

        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(detail["steps"][0]["approvers"][0]["approver_user_id"], self.approver_1.user_id)
        self.assertEqual(detail["workflow_snapshot"]["steps"][0]["members"][0]["member_ref"], "direct_manager")

    def test_direct_manager_missing_is_skipped_when_layer_has_fixed_user(self):
        self.admin_user.manager_user_id = None
        self._upsert_workflow_members(
            "knowledge_base_create",
            [
                {
                    "step_name": "Manager And Fixed",
                    "members": [
                        {"member_type": "user", "member_ref": self.approver_1.user_id},
                        {"member_type": "special_role", "member_ref": "direct_manager"},
                    ],
                }
            ],
        )

        request = self._create_dataset_request(name="Dataset Mixed Step")
        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(detail["current_step_no"], 1)
        self.assertEqual(len(detail["steps"][0]["approvers"]), 1)
        self.assertEqual(detail["steps"][0]["approvers"][0]["approver_user_id"], self.approver_1.user_id)
        self.assertIn("step_member_auto_skipped", {item["event_type"] for item in detail["events"]})

        executed = self._approve(request["request_id"], self.approver_1)
        self.assertEqual(executed["status"], "executed")

    def test_direct_manager_only_step_auto_skips_to_next_step(self):
        self.admin_user.manager_user_id = None
        self._upsert_workflow_members(
            "knowledge_base_create",
            [
                {
                    "step_name": "Manager Review",
                    "members": [{"member_type": "special_role", "member_ref": "direct_manager"}],
                },
                {
                    "step_name": "Director Review",
                    "members": [{"member_type": "user", "member_ref": self.approver_2.user_id}],
                },
            ],
        )

        request = self._create_dataset_request(name="Dataset Skip Step")
        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(detail["current_step_no"], 2)
        self.assertEqual(detail["current_step_name"], "Director Review")
        self.assertEqual(len(detail["steps"]), 1)
        self.assertEqual(detail["steps"][0]["step_no"], 2)
        self.assertIn("step_auto_skipped", {item["event_type"] for item in detail["events"]})

    def test_all_steps_skipped_execute_immediately(self):
        self.admin_user.manager_user_id = None
        self._upsert_workflow_members(
            "knowledge_base_create",
            [
                {
                    "step_name": "Manager Review",
                    "members": [{"member_type": "special_role", "member_ref": "direct_manager"}],
                }
            ],
        )

        request = self._create_dataset_request(name="Dataset Auto Execute")
        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(request["status"], "executed")
        self.assertEqual(detail["status"], "executed")
        self.assertEqual(detail["current_step_no"], None)
        event_types = {item["event_type"] for item in detail["events"]}
        self.assertIn("step_auto_skipped", event_types)
        self.assertIn("request_approved", event_types)
        self.assertIn("execution_completed", event_types)

    def test_same_user_resolved_from_fixed_and_direct_manager_is_deduplicated(self):
        self.admin_user.manager_user_id = self.approver_1.user_id
        self._upsert_workflow_members(
            "knowledge_base_create",
            [
                {
                    "step_name": "Deduplicated Step",
                    "members": [
                        {"member_type": "user", "member_ref": self.approver_1.user_id},
                        {"member_type": "special_role", "member_ref": "direct_manager"},
                    ],
                }
            ],
        )

        request = self._create_dataset_request(name="Dataset Dedup")
        detail = self.service.get_request_detail_for_user(
            request_id=request["request_id"],
            requester_user=self.admin_user,
        )

        self.assertEqual(len(detail["steps"][0]["approvers"]), 1)
        self.assertEqual(detail["steps"][0]["approvers"][0]["approver_user_id"], self.approver_1.user_id)

    def test_same_layer_requires_all_approvers_before_advancing(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [
                {"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id, self.approver_2.user_id]},
                {"step_name": "Step 2", "approver_user_ids": [self.approver_3.user_id]},
            ],
        )
        request = self._create_dataset_request(name="Dataset All Approve")

        first_detail = self._approve(request["request_id"], self.approver_1)
        self.assertEqual(first_detail["status"], "in_approval")
        self.assertEqual(first_detail["current_step_no"], 1)
        self.assertEqual(first_detail["steps"][0]["status"], "active")
        self.assertEqual(self.ragflow_service.created_payloads, [])

        second_detail = self._approve(request["request_id"], self.approver_2)
        self.assertEqual(second_detail["status"], "in_approval")
        self.assertEqual(second_detail["current_step_no"], 2)
        self.assertEqual(second_detail["current_step_name"], "Step 2")
        self.assertEqual(second_detail["steps"][0]["status"], "approved")
        self.assertEqual(second_detail["steps"][1]["status"], "active")
        self.assertEqual(self.ragflow_service.created_payloads, [])

    def test_list_requests_for_user_supports_status_filter_and_approver_history(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id]}],
        )

        executed_request = self._create_dataset_request(name="Dataset Executed For List")
        rejected_request = self._create_dataset_request(name="Dataset Rejected For List")

        self._approve(executed_request["request_id"], self.approver_1)
        self._reject(rejected_request["request_id"], self.approver_1, notes="Rejected for list")

        approver_all = self.service.list_requests_for_user(
            requester_user=self.approver_1,
            view="todo",
            status=None,
            limit=20,
        )
        approver_rejected = self.service.list_requests_for_user(
            requester_user=self.approver_1,
            view="todo",
            status="rejected",
            limit=20,
        )
        applicant_executed = self.service.list_requests_for_user(
            requester_user=self.admin_user,
            view="mine",
            status="executed",
            limit=20,
        )

        self.assertEqual({item["request_id"] for item in approver_all["items"]}, {
            executed_request["request_id"],
            rejected_request["request_id"],
        })
        self.assertEqual([item["request_id"] for item in approver_rejected["items"]], [rejected_request["request_id"]])
        self.assertEqual([item["request_id"] for item in applicant_executed["items"]], [executed_request["request_id"]])

    def test_list_requests_for_user_rejects_invalid_status_filter(self):
        with self.assertRaises(OperationApprovalServiceError) as invalid_ctx:
            self.service.list_requests_for_user(
                requester_user=self.admin_user,
                view="mine",
                status="unknown_status",
                limit=20,
            )
        self.assertEqual(invalid_ctx.exception.code, "operation_request_status_invalid")

    def test_any_reject_terminates_request(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id, self.approver_2.user_id]}],
        )
        request = self._create_dataset_request(name="Dataset Reject")

        detail = self._reject(request["request_id"], self.approver_1, notes="Not acceptable")

        self.assertEqual(detail["status"], "rejected")
        self.assertEqual(detail["steps"][0]["status"], "rejected")
        self.assertEqual(self.ragflow_service.created_payloads, [])

    def test_withdraw_respects_permissions_and_status(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id]}],
        )
        request = self._create_dataset_request(name="Dataset Withdraw")

        with self.assertRaises(OperationApprovalServiceError) as forbidden_ctx:
            self.service.withdraw_request(
                request_id=request["request_id"],
                actor_user=self.outsider_user,
                reason="not owner",
            )
        self.assertEqual(forbidden_ctx.exception.code, "operation_request_withdraw_forbidden")

        withdrawn = self.service.withdraw_request(
            request_id=request["request_id"],
            actor_user=self.admin_user,
            reason="cancel request",
        )
        self.assertEqual(withdrawn["status"], "withdrawn")

        second_request = self._create_dataset_request(name="Dataset Executed")
        executed = self._approve(second_request["request_id"], self.approver_1)
        self.assertEqual(executed["status"], "executed")

        with self.assertRaises(OperationApprovalServiceError) as state_ctx:
            self.service.withdraw_request(
                request_id=second_request["request_id"],
                actor_user=self.admin_user,
                reason="too late",
            )
        self.assertEqual(state_ctx.exception.code, "operation_request_not_withdrawable")

    def test_signature_is_required_and_invalid_signature_is_blocked(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id]}],
        )
        request = self._create_dataset_request(name="Dataset Signature")

        with self.assertRaises(OperationApprovalServiceError) as required_ctx:
            self.service.approve_request(
                request_id=request["request_id"],
                actor_user=self.approver_1,
                sign_token="",
                signature_meaning="Approval",
                signature_reason="Approve request",
                notes=None,
            )
        self.assertEqual(required_ctx.exception.code, "sign_token_required")

        other_user_token = self._issue_sign_token(self.approver_2)
        with self.assertRaises(OperationApprovalServiceError) as mismatch_ctx:
            self.service.approve_request(
                request_id=request["request_id"],
                actor_user=self.approver_1,
                sign_token=other_user_token,
                signature_meaning="Approval",
                signature_reason="Approve request",
                notes=None,
            )
        self.assertEqual(mismatch_ctx.exception.code, "sign_token_user_mismatch")

    def test_four_operations_execute_only_after_final_approval(self):
        self.ragflow_service.add_dataset(dataset_id="ds-kb-a", name="kb-a", document_count=0, chunk_count=0)
        self.ragflow_service.add_dataset(dataset_id="ds-delete", name="kb-delete", document_count=0, chunk_count=0)

        self._upsert_workflow(
            "knowledge_file_upload",
            [{"step_name": "Upload Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )
        self._upsert_workflow(
            "knowledge_file_delete",
            [{"step_name": "Delete Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Create Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )
        self._upsert_workflow(
            "knowledge_base_delete",
            [{"step_name": "Dataset Delete Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )

        existing_doc = self._seed_document(filename="delete-me.txt", content=b"delete me")
        upload_request = self._create_upload_request(filename="approved.txt", content=b"approved data")
        delete_request = self._create_delete_document_request(existing_doc.doc_id)
        create_request = self._create_dataset_request(name="Created After Approval")
        delete_dataset_request = self._create_delete_dataset_request("ds-delete")

        self.assertEqual(self.kb_store.count_documents(include_history=True), 1)
        self.assertIsNotNone(self.kb_store.get_document(existing_doc.doc_id))
        self.assertNotIn("Created After Approval", [item["name"] for item in self.ragflow_service.datasets.values()])
        self.assertIn("ds-delete", self.ragflow_service.datasets)

        upload_detail = self._approve(upload_request["request_id"], self.approver_1)
        delete_detail = self._approve(delete_request["request_id"], self.approver_1)
        create_detail = self._approve(create_request["request_id"], self.approver_1)
        delete_dataset_detail = self._approve(delete_dataset_request["request_id"], self.approver_1)

        self.assertEqual(upload_detail["status"], "executed")
        self.assertEqual(delete_detail["status"], "executed")
        self.assertEqual(create_detail["status"], "executed")
        self.assertEqual(delete_dataset_detail["status"], "executed")
        self.assertEqual(len(self.knowledge_management_manager.prepare_create_calls), 1)
        self.assertEqual(self.knowledge_management_manager.prepare_create_calls[0]["name"], "Created After Approval")
        self.assertEqual(len(self.knowledge_management_manager.create_calls), 1)
        self.assertEqual(self.knowledge_management_manager.create_calls[0]["name"], "Created After Approval")
        self.assertEqual(self.knowledge_management_manager.prepare_delete_calls, ["ds-delete"])
        self.assertEqual(self.knowledge_management_manager.delete_calls, ["ds-delete"])

        docs = self.kb_store.list_documents(include_history=True, limit=20)
        uploaded_doc = next((item for item in docs if item.filename == "approved.txt"), None)
        self.assertIsNotNone(uploaded_doc)
        self.assertEqual(uploaded_doc.status, "approved")
        self.assertEqual(uploaded_doc.reviewed_by, self.editor_user.user_id)
        self.assertEqual(uploaded_doc.review_notes, f"operation_approval:{upload_request['request_id']}")
        self.assertTrue(str(uploaded_doc.ragflow_doc_id or "").startswith("rag-doc-"))
        self.assertEqual(len(self.ragflow_service.uploaded_documents), 1)
        self.assertEqual(self.ragflow_service.uploaded_documents[0]["kb_id"], "ds-kb-a")
        self.assertEqual(self.ragflow_service.parsed_documents[0]["dataset_ref"], "ds-kb-a")
        self.assertIsNone(self.kb_store.get_document(existing_doc.doc_id))
        self.assertIn("Created After Approval", [item["name"] for item in self.ragflow_service.datasets.values()])
        self.assertNotIn("ds-delete", self.ragflow_service.datasets)

        upload_request_detail = self.service.get_request_detail_for_user(
            request_id=upload_request["request_id"],
            requester_user=self.editor_user,
        )
        self.assertEqual(upload_request_detail["artifacts"][0]["cleanup_status"], "cleaned")
        self.assertFalse(Path(upload_request_detail["artifacts"][0]["file_path"]).exists())

    def test_upload_request_executes_direct_ingestion_without_legacy_review_workflow(self):
        self.ragflow_service.add_dataset(dataset_id="ds-kb-a", name="kb-a", document_count=0, chunk_count=0)
        self._upsert_workflow(
            "knowledge_file_upload",
            [{"step_name": "Upload Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )

        upload_request = self._create_upload_request(filename="auto-approved.txt", content=b"approved data")
        upload_detail = self._approve(upload_request["request_id"], self.approver_1)

        self.assertEqual(upload_detail["status"], "executed")
        docs = self.kb_store.list_documents(include_history=True, limit=20)
        uploaded_doc = next((item for item in docs if item.filename == "auto-approved.txt"), None)
        self.assertIsNotNone(uploaded_doc)
        self.assertEqual(uploaded_doc.status, "approved")
        self.assertEqual(uploaded_doc.reviewed_by, self.editor_user.user_id)
        self.assertEqual(uploaded_doc.review_notes, f"operation_approval:{upload_request['request_id']}")
        self.assertTrue(str(uploaded_doc.ragflow_doc_id or "").startswith("rag-doc-"))
        self.assertEqual(len(self.ragflow_service.uploaded_documents), 1)
        self.assertEqual(self.ragflow_service.uploaded_documents[0]["kb_id"], "ds-kb-a")
        self.assertEqual(self.ragflow_service.parsed_documents[0]["dataset_ref"], "ds-kb-a")

    def test_execution_uses_company_scoped_deps_resolver(self):
        control_db_path = os.path.join(str(self.temp_dir), "control_auth.db")
        tenant_db_path = os.path.join(str(self.temp_dir), "tenant_auth.db")
        ensure_schema(control_db_path)
        ensure_schema(tenant_db_path)

        tenant_kb_store = KbStore(db_path=tenant_db_path)
        tenant_audit_store = AuditLogStore(db_path=tenant_db_path)
        tenant_deps = SimpleNamespace(
            kb_store=tenant_kb_store,
            audit_log_store=tenant_audit_store,
            org_directory_store=self.org_directory_store,
            org_structure_manager=self.org_structure_manager,
            notification_service=self.notification_service,
            deletion_log_store=self.deletion_log_store,
            ragflow_service=self.ragflow_service,
            knowledge_management_manager=self.knowledge_management_manager,
            upload_settings_store=None,
        )

        control_signature_service = ElectronicSignatureService(
            store=ElectronicSignatureStore(db_path=control_db_path)
        )
        control_inbox_service = UserInboxService(store=UserInboxStore(db_path=control_db_path))
        control_notification_store = NotificationStore(db_path=control_db_path)
        control_notification_service = NotificationService(
            store=control_notification_store,
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        control_notification_service.upsert_channel(
            channel_id="email-main",
            channel_type="email",
            name="Main Email",
            enabled=True,
            config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
        )
        split_service = OperationApprovalService(
            store=OperationApprovalStore(db_path=control_db_path),
            user_store=self.user_store,
            inbox_service=control_inbox_service,
            notification_service=control_notification_service,
            electronic_signature_service=control_signature_service,
            deps=self.deps,
            execution_deps_resolver=lambda company_id: tenant_deps,
        )

        self.ragflow_service.add_dataset(dataset_id="ds-kb-a", name="kb-a", document_count=0, chunk_count=0)
        split_service.upsert_workflow(
            operation_type="knowledge_file_upload",
            name="Upload Approval",
            steps=[{"step_name": "Upload Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )

        request = asyncio.run(
            split_service.create_request(
                operation_type="knowledge_file_upload",
                ctx=self._ctx(self.editor_user, _snapshot(can_upload=True, kb_names=("kb-a", "ds-kb-a"))),
                upload_file=_UploadFileStub(filename="scoped.txt", content=b"tenant scoped"),
                kb_ref="kb-a",
            )
        )
        sign_token = control_signature_service.issue_challenge(user=self.approver_1, password=SIGN_PASSWORD)[
            "sign_token"
        ]
        detail = split_service.approve_request(
            request_id=request["request_id"],
            actor_user=self.approver_1,
            sign_token=str(sign_token),
            signature_meaning="Approval",
            signature_reason="Approve request",
            notes=None,
        )

        self.assertEqual(detail["status"], "executed")
        self.assertEqual(self.kb_store.count_documents(include_history=True), 0)
        self.assertEqual(tenant_kb_store.count_documents(include_history=True), 1)
        tenant_docs = tenant_kb_store.list_documents(include_history=True, limit=20)
        self.assertEqual(tenant_docs[0].filename, "scoped.txt")
        request_row = OperationApprovalStore(db_path=control_db_path).get_request(request["request_id"])
        self.assertIsNotNone(request_row)
        self.assertEqual(request_row["company_id"], self.editor_user.company_id)

    def test_tenant_submission_writes_approver_inbox_to_control_inbox_store(self):
        control_db_path = os.path.join(str(self.temp_dir), "control_auth_notify.db")
        tenant_db_path = os.path.join(str(self.temp_dir), "tenant_auth_notify.db")
        ensure_schema(control_db_path)
        ensure_schema(tenant_db_path)

        tenant_kb_store = KbStore(db_path=tenant_db_path)
        tenant_audit_store = AuditLogStore(db_path=tenant_db_path)
        tenant_notification_store = NotificationStore(db_path=tenant_db_path)
        tenant_notification_service = NotificationService(
            store=tenant_notification_store,
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        tenant_notification_service.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="Tenant In App",
            enabled=True,
            config={},
        )
        tenant_deps = SimpleNamespace(
            kb_store=tenant_kb_store,
            audit_log_store=tenant_audit_store,
            org_directory_store=self.org_directory_store,
            org_structure_manager=self.org_structure_manager,
            notification_service=tenant_notification_service,
            deletion_log_store=self.deletion_log_store,
            ragflow_service=self.ragflow_service,
            knowledge_management_manager=self.knowledge_management_manager,
            upload_settings_store=None,
        )

        control_signature_service = ElectronicSignatureService(
            store=ElectronicSignatureStore(db_path=control_db_path)
        )
        control_inbox_service = UserInboxService(store=UserInboxStore(db_path=control_db_path))
        control_notification_store = NotificationStore(db_path=control_db_path)
        control_notification_service = NotificationService(
            store=control_notification_store,
            email_adapter=_NoopAdapter(),
            dingtalk_adapter=_NoopAdapter(),
            retry_interval_seconds=1,
        )
        control_notification_service.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="Control In App",
            enabled=True,
            config={},
        )
        split_service = OperationApprovalService(
            store=OperationApprovalStore(db_path=control_db_path),
            user_store=self.user_store,
            inbox_service=control_inbox_service,
            notification_service=control_notification_service,
            electronic_signature_service=control_signature_service,
            deps=tenant_deps,
        )

        self.ragflow_service.add_dataset(dataset_id="ds-kb-a", name="kb-a", document_count=0, chunk_count=0)
        split_service.upsert_workflow(
            operation_type="knowledge_file_upload",
            name="Upload Approval",
            steps=[{"step_name": "Upload Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )

        request = asyncio.run(
            split_service.create_request(
                operation_type="knowledge_file_upload",
                ctx=SimpleNamespace(
                    deps=tenant_deps,
                    user=self.editor_user,
                    payload=SimpleNamespace(sub=str(self.editor_user.user_id)),
                    snapshot=_snapshot(can_upload=True, kb_names=("kb-a", "ds-kb-a")),
                ),
                upload_file=_UploadFileStub(filename="notify-scope.txt", content=b"notify scoped"),
                kb_ref="kb-a",
            )
        )

        control_inbox = control_notification_service.list_inbox(
            recipient_user_id=self.approver_1.user_id,
            unread_only=False,
            limit=20,
            offset=0,
        )
        self.assertEqual(control_inbox["total"], 1)
        self.assertEqual(control_inbox["unread_count"], 1)
        self.assertEqual(control_inbox["items"][0]["event_type"], "operation_approval_todo")
        self.assertEqual(control_inbox["items"][0]["payload"]["request_id"], request["request_id"])
        self.assertEqual(len(tenant_notification_store.list_jobs(limit=20)), 0)

    def test_dataset_delete_fails_when_target_becomes_non_empty_before_execution(self):
        self.ragflow_service.add_dataset(dataset_id="ds-non-empty", name="kb-non-empty", document_count=0, chunk_count=0)
        self._upsert_workflow(
            "knowledge_base_delete",
            [{"step_name": "Delete Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )
        request = self._create_delete_dataset_request("ds-non-empty")

        self.ragflow_service.datasets["ds-non-empty"]["document_count"] = 2

        detail = self._approve(request["request_id"], self.approver_1)

        self.assertEqual(detail["status"], "execution_failed")
        self.assertEqual(detail["last_error"], "dataset_not_empty_at_execution")
        self.assertIn("ds-non-empty", self.ragflow_service.datasets)

    def test_execution_failed_when_target_is_changed_before_execution(self):
        self._upsert_workflow(
            "knowledge_file_delete",
            [{"step_name": "Delete Approval", "approver_user_ids": [self.approver_1.user_id]}],
        )
        doc = self._seed_document(filename="gone-before-approve.txt", content=b"gone")
        request = self._create_delete_document_request(doc.doc_id)

        self.kb_store.delete_document(doc.doc_id)
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        detail = self._approve(request["request_id"], self.approver_1)

        self.assertEqual(detail["status"], "execution_failed")
        self.assertEqual(detail["last_error"], "doc_not_found_at_execution")

    def test_notifications_events_and_audit_records_are_persisted(self):
        self._upsert_workflow(
            "knowledge_base_create",
            [{"step_name": "Step 1", "approver_user_ids": [self.approver_1.user_id]}],
        )
        request = self._create_dataset_request(name="Dataset Notify")
        request_id = request["request_id"]

        applicant_inbox = self.notification_service.list_inbox(
            recipient_user_id=str(self.admin_user.user_id),
            limit=20,
            offset=0,
            unread_only=False,
        )
        approver_inbox = self.notification_service.list_inbox(
            recipient_user_id=str(self.approver_1.user_id),
            limit=20,
            offset=0,
            unread_only=False,
        )
        self.assertEqual(applicant_inbox["total"], 0)
        self.assertEqual(applicant_inbox["unread_count"], 0)
        self.assertEqual(approver_inbox["total"], 1)
        self.assertEqual(approver_inbox["unread_count"], 1)

        queued_jobs = self.notification_store.list_jobs(limit=20)
        self.assertEqual(len(queued_jobs), 3)
        self.assertEqual(sum(1 for item in queued_jobs if item["status"] == "queued"), 2)

        detail = self._approve(request_id, self.approver_1)
        self.assertEqual(detail["status"], "executed")

        applicant_inbox_after = self.notification_service.list_inbox(
            recipient_user_id=str(self.admin_user.user_id),
            limit=20,
            offset=0,
            unread_only=False,
        )
        approver_inbox_after = self.notification_service.list_inbox(
            recipient_user_id=str(self.approver_1.user_id),
            limit=20,
            offset=0,
            unread_only=False,
        )
        self.assertEqual(applicant_inbox_after["total"], 0)
        self.assertEqual(applicant_inbox_after["unread_count"], 0)
        self.assertEqual(approver_inbox_after["total"], 1)
        self.assertEqual(len(self.notification_store.list_jobs(limit=20)), 4)
        self.assertEqual(
            sum(1 for item in self.notification_store.list_jobs(limit=20) if item["status"] == "queued"),
            3,
        )

        request_detail = self.service.get_request_detail_for_user(
            request_id=request_id,
            requester_user=self.admin_user,
        )
        event_types = {item["event_type"] for item in request_detail["events"]}
        self.assertIn("request_submitted", event_types)
        self.assertIn("step_activated", event_types)
        self.assertIn("request_approved", event_types)
        self.assertIn("execution_started", event_types)
        self.assertIn("execution_completed", event_types)
        self.assertIn("notification_inbox_created", event_types)
        self.assertIn("notification_external_enqueued", event_types)

        total, rows = self.audit_store.list_events(request_id=request_id, limit=20)
        self.assertGreaterEqual(total, 4)
        actions = {row.action for row in rows}
        self.assertIn("operation_approval_submit", actions)
        self.assertIn("operation_approval_approve", actions)
        self.assertIn("operation_approval_execute_start", actions)
        self.assertIn("operation_approval_execute_success", actions)
        approve_rows = [row for row in rows if row.action == "operation_approval_approve"]
        self.assertEqual(len(approve_rows), 1)
        self.assertIsNotNone(approve_rows[0].signature_id)
