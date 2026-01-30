from __future__ import annotations

from pathlib import Path

from backend.services.office_to_pdf import (
    convert_office_bytes_to_pdf_bytes,
    convert_office_path_to_pdf_bytes,
    ensure_soffice_available,
)


def convert_doc_path_to_pdf_bytes(doc_path: str | Path) -> bytes:
    # Back-compat wrapper (historical name).
    return convert_office_path_to_pdf_bytes(doc_path)


def convert_doc_bytes_to_pdf_bytes(content: bytes, *, filename: str = "input.doc") -> bytes:
    # Back-compat wrapper (historical name).
    return convert_office_bytes_to_pdf_bytes(content, filename=filename)
