from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class KbDocument:
    doc_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    status: str
    uploaded_at_ms: int
    reviewed_by: Optional[str] = None
    reviewed_at_ms: Optional[int] = None
    review_notes: Optional[str] = None
    ragflow_doc_id: Optional[str] = None
    kb_id: str = "灞曞巺"
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None

