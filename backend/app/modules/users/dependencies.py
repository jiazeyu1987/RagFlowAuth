from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.app.core.auth import get_deps, get_global_deps
from backend.app.dependencies import AppDependencies
from backend.app.modules.users.repo import UsersRepo
from backend.app.modules.users.service import UsersService


def get_scoped_permission_group_store(scoped_deps: AppDependencies):
    return getattr(scoped_deps, "permission_group_store", None)


def get_user_store(global_deps: AppDependencies = Depends(get_global_deps)):
    return global_deps.user_store


def build_users_repo(
    *,
    global_deps: AppDependencies,
    permission_group_store=None,
) -> UsersRepo:
    return UsersRepo(
        global_deps,
        permission_group_store=permission_group_store,
    )


def build_users_service(
    *,
    global_deps: AppDependencies,
    permission_group_store=None,
) -> UsersService:
    return UsersService(
        build_users_repo(
            global_deps=global_deps,
            permission_group_store=permission_group_store,
        )
    )


def get_service(
    global_deps: AppDependencies = Depends(get_global_deps),
    scoped_deps: AppDependencies = Depends(get_deps),
) -> UsersService:
    permission_group_store = get_scoped_permission_group_store(scoped_deps)
    return build_users_service(
        global_deps=global_deps,
        permission_group_store=permission_group_store,
    )


UsersServiceDep = Annotated[UsersService, Depends(get_service)]
UserStoreDep = Annotated[object, Depends(get_user_store)]
GlobalAppDepsDep = Annotated[AppDependencies, Depends(get_global_deps)]
