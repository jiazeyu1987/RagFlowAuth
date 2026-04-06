from typing import Any

from pydantic import BaseModel

from backend.models.contracts import LooseObjectModel


class PermissionGroupListEnvelope(BaseModel):
    groups: list[LooseObjectModel]


class PermissionGroupEnvelope(BaseModel):
    group: LooseObjectModel


class PermissionGroupCreateResult(BaseModel):
    message: str
    group_id: int


class PermissionGroupCreateResultEnvelope(BaseModel):
    result: PermissionGroupCreateResult


class PermissionGroupKnowledgeBasesEnvelope(BaseModel):
    knowledge_bases: list[LooseObjectModel]


class PermissionGroupKnowledgeTree(BaseModel):
    nodes: list[LooseObjectModel]
    datasets: list[LooseObjectModel]
    bindings: dict[str, Any]


class PermissionGroupKnowledgeTreeEnvelope(BaseModel):
    knowledge_tree: PermissionGroupKnowledgeTree


class PermissionGroupChatsEnvelope(BaseModel):
    chats: list[LooseObjectModel]


class PermissionGroupFolderSnapshot(BaseModel):
    folders: list[LooseObjectModel]
    group_bindings: dict[str, str | None]
    root_group_count: int


class PermissionGroupFolderSnapshotEnvelope(BaseModel):
    folder_snapshot: PermissionGroupFolderSnapshot


class PermissionGroupFolderEnvelope(BaseModel):
    folder: LooseObjectModel
