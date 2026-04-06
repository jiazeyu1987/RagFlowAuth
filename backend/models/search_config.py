from pydantic import BaseModel

from backend.models.contracts import LooseObjectModel


class SearchConfigEnvelope(BaseModel):
    config: LooseObjectModel


class SearchConfigListEnvelope(BaseModel):
    configs: list[LooseObjectModel]
    count: int
