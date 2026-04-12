import unittest
from types import SimpleNamespace

from backend.services.operation_approval.service import OperationApprovalServiceError
from backend.services.operation_approval.types import (
    SPECIAL_ROLE_DIRECT_MANAGER,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
)
from backend.services.operation_approval.workflow_builder import OperationApprovalWorkflowBuilder


class _UserStore:
    def __init__(self, users):
        self._users = {str(user.user_id): user for user in users}

    def get_by_user_id(self, user_id: str):
        return self._users.get(str(user_id))


def _error_factory(code: str, status_code: int = 400):
    return OperationApprovalServiceError(code, status_code=status_code)


class TestOperationApprovalWorkflowBuilderUnit(unittest.TestCase):
    def setUp(self):
        self.active_user = SimpleNamespace(user_id="user-active", status="active", username="active")
        self.inactive_user = SimpleNamespace(user_id="user-inactive", status="inactive", username="inactive")
        self.manager_user = SimpleNamespace(user_id="user-manager", status="active", username="manager")
        self.user_store = _UserStore([self.active_user, self.inactive_user, self.manager_user])
        self.builder = OperationApprovalWorkflowBuilder(user_store=self.user_store, error_factory=_error_factory)

    def test_build_workflow_steps_validates_members_and_users(self):
        with self.assertRaises(OperationApprovalServiceError) as empty_ctx:
            self.builder.build_workflow_steps(steps=[])
        self.assertEqual(empty_ctx.exception.code, "workflow_steps_required")

        with self.assertRaises(OperationApprovalServiceError) as invalid_type_ctx:
            self.builder.build_workflow_steps(
                steps=[{"step_name": "Step 1", "members": [{"member_type": "unknown", "member_ref": "x"}]}]
            )
        self.assertEqual(invalid_type_ctx.exception.code, "workflow_step_member_type_invalid")

        with self.assertRaises(OperationApprovalServiceError) as missing_ref_ctx:
            self.builder.build_workflow_steps(
                steps=[{"step_name": "Step 1", "members": [{"member_type": "user", "member_ref": ""}]}]
            )
        self.assertEqual(missing_ref_ctx.exception.code, "workflow_step_member_ref_required")

        with self.assertRaises(OperationApprovalServiceError) as inactive_ctx:
            self.builder.build_workflow_steps(
                steps=[
                    {
                        "step_name": "Step 1",
                        "members": [{"member_type": "user", "member_ref": self.inactive_user.user_id}],
                    }
                ]
            )
        self.assertEqual(inactive_ctx.exception.code, "workflow_approver_inactive")

        with self.assertRaises(OperationApprovalServiceError) as invalid_role_ctx:
            self.builder.build_workflow_steps(
                steps=[
                    {
                        "step_name": "Step 1",
                        "members": [{"member_type": WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE, "member_ref": "unknown"}],
                    }
                ]
            )
        self.assertEqual(invalid_role_ctx.exception.code, "workflow_step_special_role_invalid")

        normalized = self.builder.build_workflow_steps(
            steps=[
                {
                    "step_name": "Step 1",
                    "approver_user_ids": [self.active_user.user_id],
                }
            ]
        )
        self.assertEqual(normalized[0]["members"][0]["member_ref"], self.active_user.user_id)

    def test_materialize_request_steps_records_missing_manager(self):
        applicant = SimpleNamespace(user_id="applicant", manager_user_id=None)
        materialized, events = self.builder.materialize_request_steps(
            workflow_steps=[
                {
                    "step_no": 1,
                    "step_name": "Manager Approval",
                    "approval_rule": "any",
                    "members": [
                        {
                            "member_type": WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
                            "member_ref": SPECIAL_ROLE_DIRECT_MANAGER,
                        }
                    ],
                }
            ],
            applicant_user=applicant,
        )
        self.assertEqual(materialized, [])
        self.assertEqual(events[0]["event_type"], "step_member_auto_skipped")
        self.assertEqual(events[0]["payload"]["reason"], "direct_manager_missing")
        self.assertEqual(events[1]["event_type"], "step_auto_skipped")

    def test_materialize_request_steps_resolves_manager(self):
        applicant = SimpleNamespace(user_id="applicant", manager_user_id=self.manager_user.user_id)
        materialized, events = self.builder.materialize_request_steps(
            workflow_steps=[
                {
                    "step_no": 1,
                    "step_name": "Manager Approval",
                    "approval_rule": "any",
                    "members": [
                        {
                            "member_type": WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
                            "member_ref": SPECIAL_ROLE_DIRECT_MANAGER,
                        }
                    ],
                }
            ],
            applicant_user=applicant,
        )
        self.assertEqual(events, [])
        self.assertEqual(materialized[0]["approvers"][0]["user_id"], self.manager_user.user_id)
