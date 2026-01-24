from pydantic import BaseModel
from typing import Optional


class OrgDirectoryItem(BaseModel):
    id: int
    name: str
    created_at_ms: int
    updated_at_ms: int


class OrgDirectoryCreateRequest(BaseModel):
    name: str


class OrgDirectoryUpdateRequest(BaseModel):
    name: str


class OrgDirectoryAuditLogResponse(BaseModel):
    id: int
    entity_type: str
    action: str
    entity_id: Optional[int] = None
    before_name: Optional[str] = None
    after_name: Optional[str] = None
    actor_user_id: str
    actor_username: Optional[str] = None
    created_at_ms: int

