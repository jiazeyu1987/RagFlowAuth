from pydantic import BaseModel


class LooseObjectModel(BaseModel):
    class Config:
        extra = "allow"
