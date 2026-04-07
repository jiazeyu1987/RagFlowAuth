from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep
from backend.app.modules.permission_groups import resources as permission_resources
from backend.models.permission_group import (
    PermissionGroupChatsEnvelope,
    PermissionGroupKnowledgeBasesEnvelope,
    PermissionGroupKnowledgeTreeEnvelope,
)


def register_resource_routes(router: APIRouter) -> None:
    @router.get("/permission-groups/resources/knowledge-bases", response_model=PermissionGroupKnowledgeBasesEnvelope)
    async def get_knowledge_bases(
        ctx: AuthContextDep,
    ):
        return permission_resources.knowledge_bases_result(ctx)

    @router.get("/permission-groups/resources/knowledge-tree", response_model=PermissionGroupKnowledgeTreeEnvelope)
    async def get_knowledge_tree(
        ctx: AuthContextDep,
    ):
        return permission_resources.knowledge_tree_result(ctx)

    @router.get("/permission-groups/resources/chats", response_model=PermissionGroupChatsEnvelope)
    async def get_chat_agents(
        ctx: AuthContextDep,
    ):
        return permission_resources.chat_resources_result(ctx)
