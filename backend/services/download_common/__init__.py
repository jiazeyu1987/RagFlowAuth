from .utils import (
    build_content_disposition,
    build_query,
    contains_chinese,
    download_pdf_bytes,
    is_downloaded_status,
    is_truthy_flag,
    normalize_match_text,
    parse_keywords,
    parse_translator_output,
    safe_pdf_filename,
    strip_html_text,
    translate_query_for_uspto,
    translator_script_path,
)
from .manager_mixins import DownloadManagerDelegationMixin

__all__ = [
    "build_content_disposition",
    "build_query",
    "contains_chinese",
    "download_pdf_bytes",
    "is_downloaded_status",
    "is_truthy_flag",
    "normalize_match_text",
    "parse_keywords",
    "parse_translator_output",
    "safe_pdf_filename",
    "strip_html_text",
    "translate_query_for_uspto",
    "translator_script_path",
    "DownloadManagerDelegationMixin",
    "BaseDownloadManager",
    "BaseDownloadStore",
]


def __getattr__(name: str):
    if name == "BaseDownloadManager":
        from .base_download_manager import BaseDownloadManager

        return BaseDownloadManager
    if name == "BaseDownloadStore":
        from .base_download_store import BaseDownloadStore

        return BaseDownloadStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
