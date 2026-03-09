from __future__ import annotations

from typing import Any

from backend.services.download_common.base_download_store import (
    BaseDownloadStore,
    item_to_dict_common,
    session_to_dict_common,
)

from .models import PaperDownloadItem, PaperDownloadSession


class PaperDownloadStore(BaseDownloadStore[PaperDownloadSession, PaperDownloadItem]):
    SESSION_TABLE = "paper_download_sessions"
    ITEM_TABLE = "paper_download_items"
    SESSION_MODEL = PaperDownloadSession
    ITEM_MODEL = PaperDownloadItem
    CREATE_ITEM_ERROR = "create_paper_item_failed"


def session_to_dict(session: PaperDownloadSession) -> dict[str, Any]:
    return session_to_dict_common(session)


def item_to_dict(item: PaperDownloadItem) -> dict[str, Any]:
    return item_to_dict_common(item)
