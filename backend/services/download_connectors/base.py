from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DownloadSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadCandidate:
    source: str
    source_label: str
    patent_id: str
    title: str
    abstract_text: str
    publication_number: str
    publication_date: str
    inventor: str
    assignee: str
    detail_url: str
    pdf_url: str | None


class DownloadSourceConnector(Protocol):
    SOURCE_KEY: str
    SOURCE_LABEL: str

    def search(self, *, query: str, limit: int) -> list[DownloadCandidate]:
        ...
