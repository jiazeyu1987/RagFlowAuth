import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.capa.router import router as capa_router
from backend.app.modules.complaints.router import router as complaints_router
from backend.app.modules.internal_audit.router import router as internal_audit_router
from backend.app.modules.management_review.router import router as management_review_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.capa import CapaService
from backend.services.complaints import ComplaintService
from backend.services.internal_audit import InternalAuditService
from backend.services.management_review import ManagementReviewService
from backend.services.supplier_qualification import SupplierQualificationService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _Deps:
    def __init__(self, *, db_path: str, users: dict[str, SimpleNamespace]):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.user_tool_permission_store = SimpleNamespace(list_tool_ids=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)
        self.supplier_qualification_service = SupplierQualificationService(db_path=db_path)
        self.complaint_service = ComplaintService(db_path=db_path)
        self.capa_service = CapaService(db_path=db_path)
        self.internal_audit_service = InternalAuditService(db_path=db_path)
        self.management_review_service = ManagementReviewService(db_path=db_path)


def _make_user(*, user_id: str, role: str) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        status="active",
        group_id=None,
        group_ids=[],
        company_id=1,
        department_id=1,
    )


class TestGovernanceClosureApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(complaints_router, prefix="/api")
        app.include_router(capa_router, prefix="/api")
        app.include_router(internal_audit_router, prefix="/api")
        app.include_router(management_review_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_non_admin_cannot_create_complaint_case(self):
        td = make_temp_dir(prefix="ragflowauth_governance_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "reviewer-1": _make_user(user_id="reviewer-1", role="reviewer"),
            }
            app = self._build_app(current_user_id="reviewer-1", deps=_Deps(db_path=db_path, users=users))
            with TestClient(app) as client:
                response = client.post(
                    "/api/complaints/cases",
                    json={
                        "complaint_code": "CMP-001",
                        "source_channel": "customer",
                        "severity_level": "major",
                        "subject": "Complaint title",
                        "description": "Complaint description",
                        "reported_by_user_id": "reviewer-1",
                        "owner_user_id": "reviewer-1",
                    },
                )
            self.assertEqual(response.status_code, 403, response.text)
            self.assertEqual(response.json()["detail"], "admin_required")
        finally:
            cleanup_dir(td)

    def test_happy_path_complaint_capa_audit_management_review(self):
        td = make_temp_dir(prefix="ragflowauth_governance_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "qa-1": _make_user(user_id="qa-1", role="reviewer"),
            }
            deps = _Deps(db_path=db_path, users=users)
            app = self._build_app(current_user_id="admin-1", deps=deps)

            component = deps.supplier_qualification_service.upsert_component(
                component_code="ragflow-core",
                component_name="RAGFlow",
                supplier_name="RAGFlow",
                component_category="vendor_service",
                deployment_scope="shared_service",
                current_version="1.0.0",
                approved_version="1.0.0",
                supplier_approval_status="approved",
                intended_use_summary="Search and Q&A",
                qualification_summary="Qualified for intended use",
                supplier_audit_summary="Audit completed",
                known_issue_review="Known issues accepted",
                revalidation_trigger=None,
                migration_plan_summary="Upgrade by controlled plan",
                review_due_date="2027-01-01",
                approved_by_user_id="admin-1",
            )
            env_record = deps.supplier_qualification_service.record_environment_qualification(
                component_code=component["component_code"],
                environment_name="prod-main",
                company_id=None,
                release_version="2.0.0",
                protocol_ref="IQ-OQ-PQ-001",
                iq_status="passed",
                oq_status="passed",
                pq_status="passed",
                qualification_summary="Environment qualified",
                deviation_summary=None,
                executed_by_user_id="qa-1",
                approved_by_user_id="admin-1",
            )

            with TestClient(app) as client:
                complaint_resp = client.post(
                    "/api/complaints/cases",
                    json={
                        "complaint_code": "CMP-100",
                        "source_channel": "customer",
                        "severity_level": "critical",
                        "subject": "Label mismatch",
                        "description": "Packaging label mismatch found.",
                        "reported_by_user_id": "qa-1",
                        "owner_user_id": "admin-1",
                        "related_supplier_component_code": component["component_code"],
                        "related_environment_record_id": env_record["record_id"],
                    },
                )
                self.assertEqual(complaint_resp.status_code, 200, complaint_resp.text)
                complaint = complaint_resp.json()["complaint"]

                capa_resp = client.post(
                    "/api/capa/actions",
                    json={
                        "capa_code": "CAPA-100",
                        "complaint_id": complaint["complaint_id"],
                        "action_title": "Fix labeling workflow",
                        "root_cause_summary": "Missing controlled review step",
                        "correction_plan": "Add mandatory label checkpoint",
                        "preventive_plan": "Add release checklist control",
                        "owner_user_id": "admin-1",
                        "due_date": "2026-05-01",
                    },
                )
                self.assertEqual(capa_resp.status_code, 200, capa_resp.text)
                capa = capa_resp.json()["capa"]

                assess_resp = client.post(
                    f"/api/complaints/cases/{complaint['complaint_id']}/assess",
                    json={
                        "status": "capa_required",
                        "disposition_summary": "CAPA required for closure.",
                        "linked_capa_id": capa["capa_id"],
                    },
                )
                self.assertEqual(assess_resp.status_code, 200, assess_resp.text)
                self.assertEqual(assess_resp.json()["complaint"]["status"], "capa_required")

                verify_capa_resp = client.post(
                    f"/api/capa/actions/{capa['capa_id']}/verify",
                    json={"effectiveness_summary": "No recurrence in verification window"},
                )
                self.assertEqual(verify_capa_resp.status_code, 200, verify_capa_resp.text)
                self.assertEqual(verify_capa_resp.json()["capa"]["status"], "verified")

                close_capa_resp = client.post(
                    f"/api/capa/actions/{capa['capa_id']}/close",
                    json={"closure_summary": "CAPA closed with evidence package"},
                )
                self.assertEqual(close_capa_resp.status_code, 200, close_capa_resp.text)
                self.assertEqual(close_capa_resp.json()["capa"]["status"], "closed")

                close_complaint_resp = client.post(
                    f"/api/complaints/cases/{complaint['complaint_id']}/close",
                    json={"closure_summary": "Complaint closed after CAPA completion"},
                )
                self.assertEqual(close_complaint_resp.status_code, 200, close_complaint_resp.text)
                self.assertEqual(close_complaint_resp.json()["complaint"]["status"], "closed")

                audit_create_resp = client.post(
                    "/api/internal-audits/records",
                    json={
                        "audit_code": "IA-2026-01",
                        "scope_summary": "Complaint and CAPA governance audit",
                        "lead_auditor_user_id": "qa-1",
                        "planned_at_ms": 1_780_000_000_000,
                    },
                )
                self.assertEqual(audit_create_resp.status_code, 200, audit_create_resp.text)
                audit = audit_create_resp.json()["audit_record"]

                audit_complete_resp = client.post(
                    f"/api/internal-audits/records/{audit['audit_id']}/complete",
                    json={
                        "findings_summary": "One major finding and corrective evidence.",
                        "conclusion_summary": "Effective after verification.",
                        "related_capa_id": capa["capa_id"],
                    },
                )
                self.assertEqual(audit_complete_resp.status_code, 200, audit_complete_resp.text)
                self.assertEqual(audit_complete_resp.json()["audit_record"]["status"], "completed")

                mr_create_resp = client.post(
                    "/api/management-reviews/records",
                    json={
                        "review_code": "MR-2026-Q2",
                        "meeting_at_ms": 1_780_000_100_000,
                        "chair_user_id": "admin-1",
                        "input_summary": "Complaint trends and CAPA closure metrics",
                    },
                )
                self.assertEqual(mr_create_resp.status_code, 200, mr_create_resp.text)
                management_review = mr_create_resp.json()["management_review"]

                mr_complete_resp = client.post(
                    f"/api/management-reviews/records/{management_review['review_id']}/complete",
                    json={
                        "output_summary": "Resource reinforcement approved",
                        "decision_summary": "Continue quarterly review cadence",
                        "follow_up_capa_id": capa["capa_id"],
                    },
                )
                self.assertEqual(mr_complete_resp.status_code, 200, mr_complete_resp.text)
                self.assertEqual(mr_complete_resp.json()["management_review"]["status"], "completed")

            total, rows = deps.audit_log_store.list_events(limit=100)
            self.assertGreaterEqual(total, 8)
            actions = [item.action for item in rows]
            self.assertIn("complaint_case_create", actions)
            self.assertIn("capa_action_create", actions)
            self.assertIn("internal_audit_record_complete", actions)
            self.assertIn("management_review_record_complete", actions)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
