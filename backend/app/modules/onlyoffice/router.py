from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.app.core.authz import AuthContextDep
from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_kb_allowed
from backend.services.documents.models import DocumentRef
from backend.services.documents.sources.knowledge_source import KnowledgeDocumentSource
from backend.services.documents.sources.ragflow_source import RagflowDocumentSource
from backend.services.onlyoffice_security import create_file_access_token, parse_file_access_token

router = APIRouter()

SUPPORTED_EXTENSIONS = {".xls", ".xlsx", ".ppt", ".pptx"}


def _assert_preview_capability(ctx: AuthContextDep) -> None:
    snapshot = ctx.snapshot
    if snapshot.is_admin:
        return
    if not (snapshot.can_review or snapshot.can_download):
        raise HTTPException(status_code=403, detail="no_preview_permission")


def _build_public_api_base(request: Request) -> str:
    configured = str(getattr(settings, "ONLYOFFICE_PUBLIC_API_BASE_URL", "") or "").strip()
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def _document_type_for_extension(ext: str) -> str:
    e = str(ext or "").lower()
    if e in {".xls", ".xlsx"}:
        return "cell"
    if e in {".ppt", ".pptx"}:
        return "slide"
    return "word"


def _encode_onlyoffice_token(payload: dict[str, Any]) -> str:
    secret = str(getattr(settings, "ONLYOFFICE_JWT_SECRET", "") or "").strip()
    if not secret:
        return ""
    try:
        import jwt
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"onlyoffice_jwt_dependency_missing: {e}") from e
    encoded = jwt.encode(payload, secret, algorithm="HS256")
    return encoded.decode("utf-8") if isinstance(encoded, bytes) else str(encoded)


@router.post("/onlyoffice/editor-config")
async def build_editor_config(body: dict, request: Request, ctx: AuthContextDep):
    if not bool(getattr(settings, "ONLYOFFICE_ENABLED", False)):
        raise HTTPException(status_code=400, detail="onlyoffice_not_enabled")

    server_url = str(getattr(settings, "ONLYOFFICE_SERVER_URL", "") or "").strip().rstrip("/")
    if not server_url:
        raise HTTPException(status_code=400, detail="onlyoffice_server_url_missing")

    source = str(body.get("source") or "").strip().lower()
    doc_id = str(body.get("doc_id") or "").strip()
    dataset = str(body.get("dataset") or "").strip()
    filename = str(body.get("filename") or "").strip()

    if not source or not doc_id:
        raise HTTPException(status_code=400, detail="missing_source_or_doc_id")
    if source not in {"ragflow", "knowledge"}:
        raise HTTPException(status_code=400, detail="onlyoffice_source_not_supported")

    deps = ctx.deps
    _assert_preview_capability(ctx)

    if source == "ragflow":
        if not dataset:
            raise HTTPException(status_code=400, detail="missing_dataset")
        assert_kb_allowed(ctx.snapshot, resolve_kb_ref(deps, dataset).variants)
    else:
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        assert_kb_allowed(ctx.snapshot, doc.kb_id)
        if not filename:
            filename = str(doc.filename or "")

    if not filename:
        filename = f"document_{doc_id}"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"onlyoffice_extension_not_supported:{ext}")

    file_token = create_file_access_token(
        {
            "source": source,
            "doc_id": doc_id,
            "dataset": dataset,
            "filename": filename,
            "sub": str(ctx.payload.sub or ""),
        },
        ttl_seconds=int(getattr(settings, "ONLYOFFICE_FILE_TOKEN_TTL_SECONDS", 300) or 300),
    )
    api_base = _build_public_api_base(request)
    file_url = f"{api_base}/api/onlyoffice/file?token={quote(file_token, safe='')}"
    key_seed = f"{source}:{doc_id}:{dataset}:{filename}"
    doc_key = hashlib.sha256(key_seed.encode("utf-8")).hexdigest()[:64]

    config: dict[str, Any] = {
        "documentType": _document_type_for_extension(ext),
        "type": "desktop",
        "document": {
            "title": filename,
            "url": file_url,
            "fileType": ext.lstrip("."),
            "key": doc_key,
            "permissions": {
                "edit": False,
                "download": bool(ctx.snapshot.is_admin or ctx.snapshot.can_download),
                "print": bool(ctx.snapshot.is_admin or ctx.snapshot.can_download),
                "copy": bool(ctx.snapshot.is_admin or ctx.snapshot.can_download),
            },
        },
        "editorConfig": {
            "mode": "view",
            "lang": "zh-CN",
            "customization": {
                "autosave": False,
                "forcesave": False,
                "compactToolbar": True,
                "toolbarNoTabs": True,
            },
        },
    }
    signed = _encode_onlyoffice_token(config)
    if signed:
        config["token"] = signed

    return {
        "server_url": server_url,
        "filename": filename,
        "config": config,
    }


@router.get("/onlyoffice/file")
async def serve_file_by_token(token: str, request: Request):
    try:
        claims = parse_file_access_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid_onlyoffice_file_token:{e}")

    source = str(claims.get("source") or "").strip().lower()
    doc_id = str(claims.get("doc_id") or "").strip()
    dataset = str(claims.get("dataset") or "").strip()
    filename = str(claims.get("filename") or "").strip()
    if not source or not doc_id:
        raise HTTPException(status_code=400, detail="invalid_file_token_payload")

    deps = request.app.state.deps
    content: bytes
    if source == "knowledge":
        kb_source = KnowledgeDocumentSource(deps)
        doc_bytes = kb_source.get_bytes(DocumentRef(source="knowledge", doc_id=doc_id))
        content = doc_bytes.content
        filename = filename or doc_bytes.filename or f"document_{doc_id}"
    elif source == "ragflow":
        if not dataset:
            raise HTTPException(status_code=400, detail="invalid_file_token_dataset")
        rg_source = RagflowDocumentSource(deps)
        doc_bytes = rg_source.get_bytes(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))
        content = doc_bytes.content
        filename = filename or doc_bytes.filename or f"document_{doc_id}"
    else:
        raise HTTPException(status_code=400, detail="invalid_file_token_source")

    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    quoted = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quoted}",
            "Cache-Control": "no-store",
        },
    )
