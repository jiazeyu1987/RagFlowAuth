from pydantic import BaseModel

from backend.models.contracts import LooseObjectModel


class ChatEnvelope(BaseModel):
    chat: LooseObjectModel


class ChatListEnvelope(BaseModel):
    chats: list[LooseObjectModel]
    count: int
