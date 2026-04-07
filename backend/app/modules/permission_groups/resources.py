from __future__ import annotations

from backend.app.modules.permission_groups import access as permission_access
from backend.app.modules.permission_groups import contracts as permission_contracts
from backend.app.modules.permission_groups import operations as permission_operations


def knowledge_bases_result(ctx):
    return permission_operations.run_group_resource_action(
        ctx,
        action="get permission group knowledge bases",
        default_detail="permission_group_knowledge_bases_unavailable",
        loader=lambda: permission_access.list_manageable_knowledge_bases(ctx),
        wrapper=permission_contracts.wrap_knowledge_bases,
    )


def knowledge_tree_result(ctx):
    return permission_operations.run_group_resource_action(
        ctx,
        action="get permission group knowledge tree",
        default_detail="permission_group_knowledge_tree_unavailable",
        loader=lambda: permission_access.get_manageable_knowledge_tree(ctx),
        wrapper=permission_contracts.wrap_knowledge_tree,
    )


def chat_resources_result(ctx):
    return permission_operations.run_group_resource_action(
        ctx,
        action="get permission group chats",
        default_detail="permission_group_chats_unavailable",
        loader=lambda: permission_access.list_manageable_chat_resources(ctx),
        wrapper=permission_contracts.wrap_chats,
    )
