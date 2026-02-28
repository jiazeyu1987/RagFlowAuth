from typing import List, Optional

from pydantic import BaseModel, Field


class PermissionGroupCreate(BaseModel):
    group_name: str
    description: Optional[str] = ""
    folder_id: Optional[str] = None
    accessible_kbs: Optional[List[str]] = Field(default_factory=list)
    accessible_kb_nodes: Optional[List[str]] = Field(default_factory=list)
    accessible_chats: Optional[List[str]] = Field(default_factory=list)
    can_upload: bool = False
    can_review: bool = False
    can_download: bool = True
    can_delete: bool = False


class PermissionGroupUpdate(BaseModel):
    group_name: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[str] = None
    accessible_kbs: Optional[List[str]] = None
    accessible_kb_nodes: Optional[List[str]] = None
    accessible_chats: Optional[List[str]] = None
    can_upload: Optional[bool] = None
    can_review: Optional[bool] = None
    can_download: Optional[bool] = None
    can_delete: Optional[bool] = None


class PermissionGroupFolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class PermissionGroupFolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
