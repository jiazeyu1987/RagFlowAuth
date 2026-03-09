from __future__ import annotations

import logging
from typing import Any

from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import allowed_dataset_ids
from backend.services.chat_message_sources_store import content_hash_hex


def _looks_like_placeholder(doc_id: str, name: str) -> bool:
    if not name:
        return True
    n = name.strip()
    if not n:
        return True
    if n == doc_id:
        return True
    if n.startswith("document_") and doc_id in n:
        return True
    return False


def _normalize_chunk_text(value: Any, *, max_chars: int = 2000) -> str:
    if not isinstance(value, str):
        return ""
    out = value.strip()
    if len(out) > max_chars:
        out = out[:max_chars] + "..."
    return out


def _extract_doc_fields(chunk: dict) -> tuple[str, str, str, str]:
    doc_id = (
        chunk.get("document_id")
        or chunk.get("docId")
        or chunk.get("documentId")
        or chunk.get("doc_id")
        or chunk.get("id")
    )
    dataset_ref = (
        chunk.get("dataset_id")
        or chunk.get("dataset")
        or chunk.get("kb_id")
        or chunk.get("kb")
        or chunk.get("kb_name")
        or chunk.get("dataset_name")
    )
    filename = (
        chunk.get("filename")
        or chunk.get("doc_name")
        or chunk.get("document_name")
        or chunk.get("title")
        or chunk.get("name")
    )
    chunk_text = (
        chunk.get("content")
        or chunk.get("chunk")
        or chunk.get("text")
        or chunk.get("snippet")
        or chunk.get("content_with_weight")
    )
    return (
        str(doc_id or "").strip(),
        str(dataset_ref or "").strip(),
        str(filename or "").strip(),
        _normalize_chunk_text(chunk_text),
    )


def build_retrieval_sources(
    *,
    deps,
    snapshot,
    question: str,
    logger: logging.Logger | None = None,
    max_candidate_datasets: int = 6,
) -> list[dict]:
    log = logger or logging.getLogger(__name__)
    try:
        ragflow_service = getattr(deps, "ragflow_service", None)
        if ragflow_service is None:
            return []

        all_datasets = ragflow_service.list_datasets() or []
        dataset_ids = allowed_dataset_ids(snapshot, all_datasets)
        if not dataset_ids:
            return []

        dataset_candidates: list[str] = []
        for ds_id in dataset_ids:
            try:
                ds_name = ragflow_service.resolve_dataset_name(ds_id)
            except Exception:
                ds_name = None
            dataset_candidates.append(ds_name or ds_id)

        retrieval = deps.ragflow_chat_service.retrieve_chunks(
            question=question,
            dataset_ids=dataset_ids,
            page=1,
            page_size=30,
            similarity_threshold=0.2,
            top_k=30,
            keyword=False,
            highlight=False,
        )
        chunks = retrieval.get("chunks") if isinstance(retrieval, dict) else None
        if not isinstance(chunks, list):
            return []

        sources: list[dict] = []
        name_cache: dict[tuple[str, str], str] = {}
        doc_dataset_cache: dict[str, str] = {}

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            doc_id, dataset_ref, filename, chunk_text = _extract_doc_fields(chunk)
            if not doc_id:
                continue

            resolved_name = ""
            resolved_dataset = doc_dataset_cache.get(doc_id, "")

            if dataset_ref:
                try:
                    ds_name = ragflow_service.resolve_dataset_name(dataset_ref)
                except Exception:
                    ds_name = None
                candidates = [ds_name or dataset_ref]
            else:
                candidates = dataset_candidates[:max_candidate_datasets]

            if _looks_like_placeholder(doc_id, filename) or not resolved_dataset:
                for dataset_name in candidates:
                    if not dataset_name:
                        continue

                    cache_key = (dataset_name, doc_id)
                    if cache_key in name_cache:
                        resolved_name = name_cache[cache_key]
                        resolved_dataset = dataset_name
                        break

                    kb_store = getattr(deps, "kb_store", None)
                    if kb_store is not None:
                        try:
                            kb_info = resolve_kb_ref(deps, dataset_name)
                            local_doc = kb_store.get_document_by_ragflow_id(
                                doc_id,
                                kb_id=(kb_info.name or kb_info.ref),
                                kb_refs=list(kb_info.variants),
                            )
                        except Exception:
                            local_doc = None
                            kb_info = None

                        local_name = ""
                        if local_doc is not None:
                            try:
                                local_name = str(getattr(local_doc, "filename", "") or "").strip()
                            except Exception:
                                local_name = ""

                        if local_name:
                            resolved_name = local_name
                            resolved_dataset = (kb_info.name if kb_info is not None else None) or dataset_name
                            name_cache[cache_key] = local_name
                            break

                    try:
                        detail = ragflow_service.get_document_detail(doc_id, dataset_name=dataset_name)
                    except Exception:
                        detail = None
                    if isinstance(detail, dict):
                        detail_name = str(detail.get("name") or "").strip()
                        if detail_name:
                            resolved_name = detail_name
                            resolved_dataset = dataset_name
                            name_cache[cache_key] = detail_name
                            break

            if resolved_dataset:
                doc_dataset_cache[doc_id] = resolved_dataset

            final_dataset = resolved_dataset or (candidates[0] if candidates else dataset_ref)
            final_name = resolved_name or ("" if _looks_like_placeholder(doc_id, filename) else filename) or doc_id

            sources.append(
                {
                    "doc_id": doc_id,
                    "dataset": final_dataset,
                    "filename": final_name,
                    "chunk": chunk_text,
                }
            )

        return sources
    except Exception as exc:
        log.warning("[CHAT] Failed to build retrieval sources: %s", exc)
        return []


def persist_assistant_sources(
    *,
    deps,
    chat_id: str,
    session_id: str | None,
    assistant_text: str,
    sources: list[dict],
    logger: logging.Logger | None = None,
) -> None:
    if not sources or not session_id or not assistant_text:
        return

    log = logger or logging.getLogger(__name__)
    try:
        src_store = getattr(deps, "chat_message_sources_store", None)
        if not src_store:
            return
        src_store.upsert_sources(
            chat_id=chat_id,
            session_id=session_id,
            assistant_text=assistant_text,
            sources=sources,
        )
        log.info(
            "[CHAT] Persisted sources: chat_id=%s session_id=%s hash=%s count=%s",
            chat_id,
            session_id,
            content_hash_hex(assistant_text),
            len(sources),
        )
    except Exception:
        log.exception("[CHAT] Failed to persist sources")

