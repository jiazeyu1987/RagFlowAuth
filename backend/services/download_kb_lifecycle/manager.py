from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.permission_resolver import assert_can_delete, assert_can_upload, assert_kb_allowed
from backend.services.documents.document_manager import DocumentManager


@dataclass
class DownloadKbLifecycleManager:
    owner: Any

    def add_item_to_local_kb(
        self,
        *,
        session_id: str,
        item_id: int,
        ctx: Any,
        kb_ref: str,
        from_batch: bool,
        action_name: str,
        source_name: str,
        entity_source_key: str,
        entity_id_key: str,
        default_filename_prefix: str,
        add_review_notes: str,
        analysis_review_notes: str,
    ) -> dict[str, Any]:
        deps = self.owner.deps
        assert_can_upload(ctx.snapshot)
        assert_kb_allowed(ctx.snapshot, kb_ref)

        _, item = self.owner._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        existing_doc = deps.kb_store.get_document(item.added_doc_id) if item.added_doc_id else None
        if existing_doc:
            if item.added_analysis_doc_id or not str(item.analysis_file_path or "").strip():
                return {
                    "item": self.owner._serialize_item(item),
                    "document": {
                        "doc_id": existing_doc.doc_id,
                        "filename": existing_doc.filename,
                        "kb_id": existing_doc.kb_id,
                        "ragflow_doc_id": existing_doc.ragflow_doc_id,
                        "status": existing_doc.status,
                    },
                    "already_added": True,
                }

        try:
            if existing_doc is not None:
                updated = existing_doc
            else:
                content = self.owner._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
                updated = self.owner._upload_blob_to_kb(
                    ctx=ctx,
                    kb_ref=kb_ref,
                    filename=(item.filename or f"{default_filename_prefix}_{item_id}.pdf"),
                    content=content,
                    mime_type=(item.mime_type or self.owner._MIME_TYPE_DEFAULT),
                    review_notes=add_review_notes,
                )

            analysis_doc_id = item.added_analysis_doc_id
            analysis_path = str(item.analysis_file_path or "").strip()
            if analysis_path and not analysis_doc_id:
                analysis_file = Path(analysis_path)
                if analysis_file.exists() and analysis_file.is_file():
                    analysis_content = analysis_file.read_bytes()
                    analysis_name = analysis_file.name or f"{Path(item.filename or f'{default_filename_prefix}_{item_id}.pdf').stem}.analysis.txt"
                    analysis_doc = self.owner._upload_blob_to_kb(
                        ctx=ctx,
                        kb_ref=kb_ref,
                        filename=analysis_name,
                        content=analysis_content,
                        mime_type="text/plain; charset=utf-8",
                        review_notes=analysis_review_notes,
                    )
                    analysis_doc_id = analysis_doc.doc_id

            marked = self.owner.store.mark_item_added(
                session_id=session_id,
                item_id=item_id,
                added_doc_id=updated.doc_id,
                added_analysis_doc_id=analysis_doc_id,
                ragflow_doc_id=updated.ragflow_doc_id,
            )
            if not marked:
                raise RuntimeError("mark_item_added_failed")

            self.owner._audit_manager.safe_log_ctx_event(
                ctx=ctx,
                action=action_name,
                source=source_name,
                doc_id=updated.doc_id,
                filename=updated.filename,
                kb_id=(updated.kb_name or updated.kb_id),
                kb_dataset_id=getattr(updated, "kb_dataset_id", None),
                kb_name=getattr(updated, "kb_name", None) or (updated.kb_name or updated.kb_id),
                meta={
                    "session_id": session_id,
                    "item_id": int(item_id),
                    entity_source_key: item.source,
                    entity_id_key: item.patent_id,
                    "batch": bool(from_batch),
                    "kb_ref": kb_ref,
                },
            )

            return {
                "item": self.owner._serialize_item(marked),
                "document": {
                    "doc_id": updated.doc_id,
                    "filename": updated.filename,
                    "kb_id": (updated.kb_name or updated.kb_id),
                    "ragflow_doc_id": updated.ragflow_doc_id,
                    "status": updated.status,
                },
                "already_added": False,
            }
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=str(e)) from e

    def add_all_to_local_kb(
        self,
        *,
        session_id: str,
        ctx: Any,
        kb_ref: str,
        session_not_found_detail: str,
        action_name: str,
        source_name: str,
        item_add_fn,
    ) -> dict[str, Any]:
        session = self.owner.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=session_not_found_detail)
        self.owner._assert_session_access(session, ctx)

        items = self.owner.store.list_items(session_id=session_id)
        success = 0
        failed = 0
        details: list[dict[str, Any]] = []
        for item in items:
            if not self.owner._is_downloaded_status(item.status):
                continue
            if item.added_doc_id:
                details.append({"item_id": item.item_id, "ok": True, "already_added": True})
                continue
            try:
                item_add_fn(session_id=session_id, item_id=item.item_id, ctx=ctx, kb_ref=kb_ref, from_batch=True)
                success += 1
                details.append({"item_id": item.item_id, "ok": True})
            except Exception as e:
                failed += 1
                details.append({"item_id": item.item_id, "ok": False, "error": str(e)})

        self.owner._audit_manager.safe_log_ctx_event(
            ctx=ctx,
            action=action_name,
            source=source_name,
            meta={"session_id": session_id, "kb_ref": kb_ref, "success": success, "failed": failed},
        )

        return {
            "success": success,
            "failed": failed,
            "items": details,
            "session": self.owner.get_session_payload(session_id=session_id, ctx=ctx),
        }

    def delete_item(
        self,
        *,
        session_id: str,
        item_id: int,
        ctx: Any,
        delete_local_kb: bool,
        not_found_detail: str,
        action_name: str,
        source_name: str,
    ) -> dict[str, Any]:
        _, item = self.owner._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        deleted_file = False
        deleted_analysis_file = False
        deleted_doc = False
        deleted_analysis_doc = False

        if delete_local_kb and item.added_doc_id:
            assert_can_delete(ctx.snapshot)
            doc = self.owner.deps.kb_store.get_document(item.added_doc_id)
            if doc:
                assert_kb_allowed(ctx.snapshot, doc.kb_id)
                DocumentManager(self.owner.deps).delete_knowledge_document(doc_id=doc.doc_id, ctx=ctx)
                deleted_doc = True
        if delete_local_kb and item.added_analysis_doc_id:
            assert_can_delete(ctx.snapshot)
            analysis_doc = self.owner.deps.kb_store.get_document(item.added_analysis_doc_id)
            if analysis_doc:
                assert_kb_allowed(ctx.snapshot, analysis_doc.kb_id)
                DocumentManager(self.owner.deps).delete_knowledge_document(doc_id=analysis_doc.doc_id, ctx=ctx)
                deleted_analysis_doc = True

        path_text = str(item.file_path or "").strip()
        if path_text:
            p = Path(path_text)
            if p.exists():
                try:
                    p.unlink()
                    deleted_file = True
                except Exception:
                    pass
        analysis_path_text = str(item.analysis_file_path or "").strip()
        if analysis_path_text:
            ap = Path(analysis_path_text)
            if ap.exists():
                try:
                    ap.unlink()
                    deleted_analysis_file = True
                except Exception:
                    pass

        deleted = self.owner.store.delete_item(session_id=session_id, item_id=item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=not_found_detail)

        self.owner._audit_manager.safe_log_ctx_event(
            ctx=ctx,
            action=action_name,
            source=source_name,
            meta={
                "session_id": session_id,
                "item_id": int(item_id),
                "deleted_file": bool(deleted_file),
                "deleted_analysis_file": bool(deleted_analysis_file),
                "deleted_doc": bool(deleted_doc),
                "deleted_analysis_doc": bool(deleted_analysis_doc),
                "delete_local_kb": bool(delete_local_kb),
            },
        )

        return {
            "ok": True,
            "item_id": int(item_id),
            "deleted_file": bool(deleted_file),
            "deleted_analysis_file": bool(deleted_analysis_file),
            "deleted_doc": bool(deleted_doc),
            "deleted_analysis_doc": bool(deleted_analysis_doc),
        }

    def delete_session(
        self,
        *,
        session_id: str,
        ctx: Any,
        delete_local_kb: bool,
        session_not_found_detail: str,
        action_name: str,
        source_name: str,
    ) -> dict[str, Any]:
        session = self.owner.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=session_not_found_detail)
        self.owner._assert_session_access(session, ctx)

        job = self.owner._cancel_job(session_id)
        if job and job.is_alive():
            job.join(timeout=2.0)

        items = self.owner.store.list_items(session_id=session_id)
        deleted_files = 0
        deleted_docs = 0
        doc_errors: list[dict[str, Any]] = []

        if delete_local_kb:
            assert_can_delete(ctx.snapshot)
            mgr = DocumentManager(self.owner.deps)
            for item in items:
                if item.added_doc_id:
                    doc = self.owner.deps.kb_store.get_document(item.added_doc_id)
                    if doc:
                        try:
                            assert_kb_allowed(ctx.snapshot, doc.kb_id)
                            mgr.delete_knowledge_document(doc_id=doc.doc_id, ctx=ctx)
                            deleted_docs += 1
                        except Exception as e:
                            doc_errors.append({"item_id": item.item_id, "doc_id": doc.doc_id, "error": str(e)})
                if item.added_analysis_doc_id:
                    analysis_doc = self.owner.deps.kb_store.get_document(item.added_analysis_doc_id)
                    if analysis_doc:
                        try:
                            assert_kb_allowed(ctx.snapshot, analysis_doc.kb_id)
                            mgr.delete_knowledge_document(doc_id=analysis_doc.doc_id, ctx=ctx)
                            deleted_docs += 1
                        except Exception as e:
                            doc_errors.append({"item_id": item.item_id, "doc_id": analysis_doc.doc_id, "error": str(e)})

        for item in items:
            path_text = str(item.file_path or "").strip()
            if path_text:
                p = Path(path_text)
                if p.exists():
                    try:
                        p.unlink()
                        deleted_files += 1
                    except Exception:
                        pass
            analysis_path_text = str(item.analysis_file_path or "").strip()
            if analysis_path_text:
                ap = Path(analysis_path_text)
                if ap.exists():
                    try:
                        ap.unlink()
                        deleted_files += 1
                    except Exception:
                        pass

        try:
            root = self.owner._download_root() / str(session.created_by) / session_id
            if root.exists():
                for p in sorted(root.rglob("*"), reverse=True):
                    if p.is_file():
                        continue
                    try:
                        p.rmdir()
                    except Exception:
                        pass
                try:
                    root.rmdir()
                except Exception:
                    pass
        except Exception:
            pass

        store_result = self.owner.store.delete_session(session_id=session_id)
        deleted_items = int(store_result.get("deleted_items", 0))

        self.owner._audit_manager.safe_log_ctx_event(
            ctx=ctx,
            action=action_name,
            source=source_name,
            meta={
                "session_id": session_id,
                "delete_local_kb": bool(delete_local_kb),
                "deleted_items": deleted_items,
                "deleted_files": deleted_files,
                "deleted_docs": deleted_docs,
                "doc_error_count": len(doc_errors),
            },
        )

        self.owner._finish_job(session_id)
        return {
            "ok": True,
            "deleted_items": deleted_items,
            "deleted_files": deleted_files,
            "deleted_docs": deleted_docs,
            "doc_errors": doc_errors,
        }
