import os
import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from backend.database.schema.ensure import ensure_schema
from backend.services.approval import ApprovalWorkflowError, ApprovalWorkflowService, ApprovalWorkflowStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


@dataclass
class _Doc:
    doc_id: str
    kb_id: str
    kb_dataset_id: str | None = None
    kb_name: str | None = None
    filename: str = "doc.txt"
    uploaded_by: str = "uploader-1"
    uploaded_at_ms: int = 1


def _user(
    *,
    user_id: str,
    role: str = "reviewer",
    company_id: int = 1,
    department_id: int = 10,
    group_ids: list[int] | None = None,
):
    return SimpleNamespace(
        user_id=user_id,
        role=role,
        status="active",
        company_id=company_id,
        department_id=department_id,
        group_ids=list(group_ids or []),
        group_id=None,
    )


class TestApprovalWorkflowUnit(unittest.TestCase):
    def test_rejects_non_current_step_actor(self):
        td = make_temp_dir(prefix="ragflowauth_workflow")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A",
                steps=[
                    {"step_no": 1, "step_name": "First", "approver_user_id": "reviewer-a"},
                    {"step_no": 2, "step_name": "Second", "approver_user_id": "reviewer-b"},
                ],
            )

            doc = _Doc(doc_id="doc-a", kb_id="kb-a", kb_dataset_id="ds-a", kb_name="kb-a")
            with self.assertRaises(ApprovalWorkflowError) as exc:
                service.approve_step(
                    doc=doc,
                    actor="reviewer-b",
                    actor_user=_user(user_id="reviewer-b"),
                    notes="wrong reviewer",
                    final=False,
                )
            self.assertEqual(exc.exception.code, "approval_actor_not_assigned_to_step")
        finally:
            cleanup_dir(td)

    def test_serial_steps_bind_to_distinct_users(self):
        td = make_temp_dir(prefix="ragflowauth_workflow_serial")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            workflow = service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A",
                steps=[
                    {"step_no": 1, "step_name": "First", "approver_user_id": "reviewer-a"},
                    {"step_no": 2, "step_name": "Second", "approver_user_id": "reviewer-b"},
                ],
            )
            self.assertEqual(workflow["steps"][0]["approver_user_id"], "reviewer-a")
            self.assertEqual(workflow["steps"][1]["approver_user_id"], "reviewer-b")

            reviewer_a = _user(user_id="reviewer-a")
            reviewer_b = _user(user_id="reviewer-b")
            doc = _Doc(doc_id="doc-a", kb_id="kb-a", kb_dataset_id="ds-a", kb_name="kb-a")

            progress_1 = service.approval_progress(doc=doc, user=reviewer_a)
            self.assertTrue(progress_1["can_review_current_step"])
            self.assertEqual(progress_1["current_step_no"], 1)

            step_1 = service.approve_step(
                doc=doc,
                actor="reviewer-a",
                actor_user=reviewer_a,
                notes="step 1 ok",
                final=False,
            )
            self.assertEqual(step_1["current_step_no"], 2)
            self.assertEqual(step_1["approval_status"], "in_progress")

            self.assertFalse(service.approval_progress(doc=doc, user=reviewer_a)["can_review_current_step"])
            self.assertTrue(service.approval_progress(doc=doc, user=reviewer_b)["can_review_current_step"])

            with self.assertRaises(ApprovalWorkflowError) as exc:
                service.approve_step(
                    doc=doc,
                    actor="reviewer-a",
                    actor_user=reviewer_a,
                    notes="should fail on step 2",
                    final=True,
                )
            self.assertEqual(exc.exception.code, "approval_actor_not_assigned_to_step")

            final_step = service.approve_step(
                doc=doc,
                actor="reviewer-b",
                actor_user=reviewer_b,
                notes="step 2 ok",
                final=True,
            )
            self.assertEqual(final_step["approval_status"], "approved")
            self.assertEqual(final_step["current_step_no"], 2)
        finally:
            cleanup_dir(td)

    def test_company_boundary_filters_pending_reviews(self):
        td = make_temp_dir(prefix="ragflowauth_workflow_scope")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ApprovalWorkflowService(store=ApprovalWorkflowStore(db_path=db_path))
            service.upsert_workflow(
                workflow_id="wf-kb-a",
                kb_ref="kb-a",
                name="KB-A",
                steps=[
                    {
                        "step_no": 1,
                        "step_name": "QA Review",
                        "approver_role": "reviewer",
                        "approver_company_id": 1,
                        "approval_mode": "all",
                    },
                    {"step_no": 2, "step_name": "Final", "approver_user_id": "reviewer-b"},
                ],
            )

            docs = [
                _Doc(doc_id="doc-a", kb_id="kb-a", kb_dataset_id="ds-a", kb_name="kb-a"),
                _Doc(doc_id="doc-b", kb_id="kb-a", kb_dataset_id="ds-a", kb_name="kb-a"),
            ]
            company_1_user = _user(user_id="reviewer-a", role="reviewer", company_id=1)
            company_2_user = _user(user_id="reviewer-c", role="reviewer", company_id=2)

            items_company_1 = service.get_pending_reviews_for_user(docs=docs, user=company_1_user)
            items_company_2 = service.get_pending_reviews_for_user(docs=docs, user=company_2_user)
            self.assertEqual({item["doc_id"] for item in items_company_1}, {"doc-a", "doc-b"})
            self.assertEqual(items_company_2, [])
        finally:
            cleanup_dir(td)
