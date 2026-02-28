from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class PaperSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaperCandidate:
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
    pdf_url: Optional[str]

