from __future__ import annotations

from typing import Any

from backend.services.download_common.base_download_store import (
    BaseDownloadStore,
    item_to_dict_common,
    session_to_dict_common,
)

from .models import PatentDownloadItem, PatentDownloadSession


class PatentDownloadStore(BaseDownloadStore[PatentDownloadSession, PatentDownloadItem]):
    SESSION_TABLE = "patent_download_sessions"
    ITEM_TABLE = "patent_download_items"
    SESSION_MODEL = PatentDownloadSession
    ITEM_MODEL = PatentDownloadItem
    CREATE_ITEM_ERROR = "create_patent_item_failed"


def session_to_dict(session: PatentDownloadSession) -> dict[str, Any]:
    return session_to_dict_common(session)


def item_to_dict(item: PatentDownloadItem) -> dict[str, Any]:
    return item_to_dict_common(item)
