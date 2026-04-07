import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.app.modules.users import passwords as user_passwords


class _Service:
    def __init__(self):
        self.calls = []

    def reset_password(self, user_id, new_password):
        self.calls.append((user_id, new_password))


class UsersPasswordsUnitTest(unittest.TestCase):
    def test_reset_password_result_resolves_target_resets_and_audits(self):
        service = _Service()
        ctx = SimpleNamespace(user=SimpleNamespace(user_id="u-admin"))
        deps = SimpleNamespace(user_store=object(), audit_log_manager=object())
        request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"), client=SimpleNamespace(host="127.0.0.1"))
        target_user = SimpleNamespace(user_id="u-1", username="alice")

        with patch.object(user_passwords, "resolve_password_reset_target", return_value=target_user) as resolve_target, patch.object(
            user_passwords, "assert_can_reset_password"
        ) as assert_can_reset_password, patch.object(user_passwords, "log_password_reset_event") as log_event:
            result = user_passwords.reset_password_result(
                ctx=ctx,
                deps=deps,
                request=request,
                service=service,
                user_id="u-1",
                new_password="Password123",
            )

        resolve_target.assert_called_once_with(ctx, deps.user_store, "u-1")
        assert_can_reset_password.assert_called_once_with(ctx, target_user)
        self.assertEqual(service.calls, [("u-1", "Password123")])
        log_event.assert_called_once_with(
            deps=deps,
            request=request,
            actor_user=ctx.user,
            target_user=target_user,
            user_id="u-1",
        )
        self.assertEqual(result, {"result": {"message": "password_reset"}})

    def test_reset_password_result_fails_fast_when_target_is_not_authorized(self):
        service = _Service()
        ctx = SimpleNamespace(user=SimpleNamespace(user_id="u-sub"))
        deps = SimpleNamespace(user_store=object(), audit_log_manager=object())
        request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"), client=SimpleNamespace(host="127.0.0.1"))
        target_user = SimpleNamespace(user_id="u-2", username="bob")

        with patch.object(user_passwords, "resolve_password_reset_target", return_value=target_user), patch.object(
            user_passwords,
            "assert_can_reset_password",
            side_effect=HTTPException(status_code=403, detail="admin_required"),
        ), patch.object(user_passwords, "log_password_reset_event") as log_event:
            with self.assertRaises(HTTPException) as ctx_err:
                user_passwords.reset_password_result(
                    ctx=ctx,
                    deps=deps,
                    request=request,
                    service=service,
                    user_id="u-2",
                    new_password="Password123",
                )

        self.assertEqual(ctx_err.exception.status_code, 403)
        self.assertEqual(ctx_err.exception.detail, "admin_required")
        self.assertEqual(service.calls, [])
        log_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
