from __future__ import annotations

import hashlib
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.app.core.tenant import company_id_from_payload
from backend.app.core.authz import AuthContextDep
from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_kb_allowed
from backend.app.dependencies import get_tenant_dependencies
from backend.services.documents.models import DocumentRef
from backend.services.documents.sources.knowledge_source import KnowledgeDocumentSource
from backend.services.documents.sources.ragflow_source import RagflowDocumentSource
from backend.services.onlyoffice_security import create_file_access_token, parse_file_access_token
from backend.services.watermarking import DocumentWatermarkService

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


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
def build_editor_config(body: dict, request: Request, ctx: AuthContextDep):
    t0 = time.perf_counter()
    request_id = getattr(getattr(request, "state", None), "request_id", "") or "-"
    source = str(body.get("source") or "").strip().lower()
    doc_id = str(body.get("doc_id") or "").strip()
    dataset = str(body.get("dataset") or "").strip()
    filename = str(body.get("filename") or "").strip()
    logger.info(
        "onlyoffice_editor_config_start request_id=%s source=%s doc_id=%s dataset=%s filename=%s",
        request_id,
        source,
        doc_id,
        dataset,
        filename,
    )
    if not bool(getattr(settings, "ONLYOFFICE_ENABLED", False)):
        raise HTTPException(status_code=400, detail="onlyoffice_not_enabled")

    server_url = str(getattr(settings, "ONLYOFFICE_SERVER_URL", "") or "").strip().rstrip("/")
    if not server_url:
        raise HTTPException(status_code=400, detail="onlyoffice_server_url_missing")

    if not source or not doc_id:
        raise HTTPException(status_code=400, detail="missing_source_or_doc_id")
    if source not in {"ragflow", "knowledge"}:
        raise HTTPException(status_code=400, detail="onlyoffice_source_not_supported")

    deps = ctx.deps

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

    watermark = DocumentWatermarkService(
        store=getattr(deps, "watermark_policy_store", None),
        org_structure_manager=getattr(deps, "org_structure_manager", None),
    ).build_watermark(
        user=getattr(ctx, "user", None),
        payload_sub=getattr(ctx.payload, "sub", None),
        purpose="preview",
        doc_id=doc_id,
        filename=filename,
        source=source,
    )

    file_token = create_file_access_token(
        {
            "source": source,
            "doc_id": doc_id,
            "dataset": dataset,
            "filename": filename,
            "sub": str(ctx.payload.sub or ""),
            "cid": getattr(getattr(ctx, "user", None), "company_id", None),
            "watermark_policy_id": watermark.get("policy_id"),
            "watermark_text": watermark.get("text"),
            "watermark_purpose": watermark.get("purpose"),
        },
        ttl_seconds=int(getattr(settings, "ONLYOFFICE_FILE_TOKEN_TTL_SECONDS", 300) or 300),
    )
    api_base = _build_public_api_base(request)
    file_url = f"{api_base}/api/onlyoffice/file?token={quote(file_token, safe='')}"
    can_download = bool(ctx.snapshot.is_admin or ctx.snapshot.can_download)
    can_print = can_download
    can_copy = bool(ctx.snapshot.is_admin or ctx.snapshot.can_copy)
    # IMPORTANT:
    # ONLYOFFICE reuses cached sessions by `document.key`. If key stays stable while
    # permission policy changes, old permission behavior can appear to "stick".
    # Bind the key to user + permission profile + a policy version to force refresh.
    key_seed = (
        f"preview-v2:{source}:{doc_id}:{dataset}:{filename}:"
        f"{ctx.payload.sub or ''}:d{int(can_download)}:p{int(can_print)}:c{int(can_copy)}:"
        f"w{str(watermark.get('policy_id') or '')}"
    )
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
                "download": can_download,
                "print": can_print,
                "copy": can_copy,
            },
        },
        "editorConfig": {
            "mode": "view",
            "lang": "zh-CN",
            "watermark": watermark,
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

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "onlyoffice_editor_config_done request_id=%s source=%s doc_id=%s dataset=%s ext=%s perms=d%s/p%s/c%s key=%s elapsed_ms=%.2f",
        request_id,
        source,
        doc_id,
        dataset,
        ext,
        int(can_download),
        int(can_print),
        int(can_copy),
        doc_key[:12],
        elapsed_ms,
    )
    return {
        "server_url": server_url,
        "filename": filename,
        "watermark": watermark,
        "watermark_text": watermark.get("text"),
        "watermark_policy_id": watermark.get("policy_id"),
        "config": config,
    }


@router.get("/onlyoffice/file")
def serve_file_by_token(token: str, request: Request):
    t0 = time.perf_counter()
    request_id = getattr(getattr(request, "state", None), "request_id", "") or "-"
    logger.info("onlyoffice_file_start request_id=%s", request_id)
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

    try:
        company_id = company_id_from_payload(claims)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"invalid_file_token_company_id:{e}") from e

    if company_id is None:
        deps = request.app.state.deps
    else:
        deps = get_tenant_dependencies(request.app, company_id=company_id)
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
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "onlyoffice_file_served request_id=%s source=%s doc_id=%s dataset=%s filename=%s size_bytes=%s elapsed_ms=%.2f",
        request_id,
        source,
        doc_id,
        dataset,
        filename,
        len(content),
        elapsed_ms,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quoted}",
            "Cache-Control": "no-store",
            "X-Watermark-Policy-Id": str(claims.get("watermark_policy_id") or ""),
        },
    )
