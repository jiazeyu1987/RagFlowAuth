import unittest

from fastapi import HTTPException
from pydantic import BaseModel

from backend.app.modules.users import contracts as user_contracts


class _UserModel(BaseModel):
    user_id: str
    username: str


class UsersContractsUnitTest(unittest.TestCase):
    def test_normalize_user_payload_accepts_dict_and_pydantic_model(self):
        self.assertEqual(
            user_contracts.normalize_user_payload({"user_id": "u-1"}),
            {"user_id": "u-1"},
        )
        self.assertEqual(
            user_contracts.normalize_user_payload(_UserModel(user_id="u-2", username="alice")),
            {"user_id": "u-2", "username": "alice"},
        )

    def test_normalize_user_payload_fails_fast_on_invalid_payload(self):
        with self.assertRaises(HTTPException) as ctx:
            user_contracts.normalize_user_payload(["bad"])

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "user_invalid_payload")

    def test_wrap_user_action_wraps_action_result_in_user_envelope(self):
        result = user_contracts.wrap_user_action(lambda: {"user_id": "u-3", "username": "bob"})

        self.assertEqual(
            result,
            {"user": {"user_id": "u-3", "username": "bob"}},
        )

    def test_run_result_action_runs_action_and_returns_result_envelope(self):
        calls = []

        result = user_contracts.run_result_action(
            lambda: calls.append("ran"),
            message="user_deleted",
        )

        self.assertEqual(calls, ["ran"])
        self.assertEqual(result, {"result": {"message": "user_deleted"}})

    def test_contract_actions_forward_args_and_kwargs_without_lambda_wrappers(self):
        calls = []

        result = user_contracts.wrap_user_action(
            lambda user_id, *, username: {"user_id": user_id, "username": username},
            "u-5",
            username="carol",
        )
        message_result = user_contracts.run_result_action(
            lambda user_id, *, calls: calls.append(user_id),
            "u-6",
            calls=calls,
            message="user_deleted",
        )

        self.assertEqual(result, {"user": {"user_id": "u-5", "username": "carol"}})
        self.assertEqual(calls, ["u-6"])
        self.assertEqual(message_result, {"result": {"message": "user_deleted"}})

    def test_action_helpers_support_keyword_only_service_style_callables(self):
        user_result = user_contracts.wrap_user_action(
            lambda *, user_id: {"user_id": user_id},
            user_id="u-4",
        )
        message_result = user_contracts.run_result_action(
            lambda user_id: ("deleted", user_id),
            "u-4",
            message="user_deleted",
        )

        self.assertEqual(user_result, {"user": {"user_id": "u-4"}})
        self.assertEqual(message_result, {"result": {"message": "user_deleted"}})


if __name__ == "__main__":
    unittest.main()
