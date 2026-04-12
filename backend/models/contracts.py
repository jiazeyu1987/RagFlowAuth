from pydantic import BaseModel, ConfigDict


class LooseObjectModel(BaseModel):
    model_config = ConfigDict(extra="allow")
