"""
Unified document operations (preview/download/upload/delete) across sources.

Sources:
- knowledge: local uploaded documents stored in kb_store
- ragflow: documents stored in RAGFlow (download/delete via ragflow_service)

This package provides a single management entrypoint: `DocumentManager`.
"""

