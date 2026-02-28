from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PatentDownloadSession:
    session_id: str
    created_by: str
    created_at_ms: int
    keyword_text: str
    keywords_json: str
    use_and: bool
    sources_json: str
    status: str
    error: Optional[str]
    source_errors_json: str
    source_stats_json: str


@dataclass(frozen=True)
class PatentDownloadItem:
    item_id: int
    session_id: str
    source: str
    source_label: str
    patent_id: Optional[str]
    title: Optional[str]
    abstract_text: Optional[str]
    publication_number: Optional[str]
    publication_date: Optional[str]
    inventor: Optional[str]
    assignee: Optional[str]
    detail_url: Optional[str]
    pdf_url: Optional[str]
    file_path: Optional[str]
    filename: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    status: str
    error: Optional[str]
    analysis_text: Optional[str]
    analysis_file_path: Optional[str]
    added_doc_id: Optional[str]
    added_analysis_doc_id: Optional[str]
    ragflow_doc_id: Optional[str]
    added_at_ms: Optional[int]
    created_at_ms: int
