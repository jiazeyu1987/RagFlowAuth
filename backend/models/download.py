from pydantic import BaseModel


class DownloadSessionStopResult(BaseModel):
    message: str
    session_id: str
    status: str
    already_finished: bool


class DownloadSessionStopResultEnvelope(BaseModel):
    result: DownloadSessionStopResult
