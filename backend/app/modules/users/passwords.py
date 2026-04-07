from __future__ import annotations

from backend.app.modules.users.access import (
    assert_can_reset_password,
    resolve_password_reset_target,
)
from backend.app.modules.users.audit import log_password_reset_event
from backend.app.modules.users.contracts import run_result_action


def _get_authorized_reset_target(*, ctx, user_store, user_id: str):
    target_user = resolve_password_reset_target(ctx, user_store, user_id)
    assert_can_reset_password(ctx, target_user)
    return target_user


def _log_password_reset(ctx, deps, request, target_user, *, user_id: str) -> None:
    log_password_reset_event(
        deps=deps,
        request=request,
        actor_user=ctx.user,
        target_user=target_user,
        user_id=user_id,
    )


def _reset_password_and_audit(*, ctx, deps, request, service, target_user, user_id: str, new_password: str) -> None:
    service.reset_password(user_id=user_id, new_password=new_password)
    _log_password_reset(ctx, deps, request, target_user, user_id=user_id)


def reset_password_result(*, ctx, deps, request, service, user_id: str, new_password: str):
    target_user = _get_authorized_reset_target(
        ctx=ctx,
        user_store=deps.user_store,
        user_id=user_id,
    )

    return run_result_action(
        _reset_password_and_audit,
        ctx=ctx,
        deps=deps,
        request=request,
        service=service,
        target_user=target_user,
        user_id=user_id,
        new_password=new_password,
        message="password_reset",
    )
