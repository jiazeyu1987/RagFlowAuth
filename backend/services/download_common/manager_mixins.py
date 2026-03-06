from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from . import utils as download_common_utils
from backend.services.llm_analysis import LLMAnalysisManager
from backend.services.unified_preview import build_preview_payload


class DownloadManagerDelegationMixin:
    _DM_KIND = "download"
    _DM_SOURCE_NAME = "download"
    _DM_DEFAULT_LOCAL_KB_REF = "[local]"
    _DM_ENTITY_SOURCE_KEY = "source"
    _DM_ENTITY_ID_KEY = "entity_id"
    _DM_DEFAULT_FILENAME_PREFIX = "item"
    _DM_ADD_REVIEW_NOTES = "added_from_download"
    _DM_ANALYSIS_REVIEW_NOTES = "added_analysis_from_download"
    _MIME_TYPE_DEFAULT = "application/pdf"
    _DOWNLOAD_USER_AGENT = "Mozilla/5.0"

    @staticmethod
    def _history_group_from_session(session: Any) -> tuple[str, list[str], bool]:
        keywords: list[str] = []
        try:
            raw = json.loads(str(getattr(session, "keywords_json", "") or "[]"))
            if isinstance(raw, list):
                for value in raw:
                    text = str(value or "").strip()
                    if text:
                        keywords.append(text)
        except Exception:
            keywords = []
        use_and = bool(getattr(session, "use_and", False))
        normalized = sorted({k.lower() for k in keywords if k.strip()})
        group_key = f"{'and' if use_and else 'or'}::{'|'.join(normalized)}"
        return group_key, keywords, use_and

    @staticmethod
    def _history_item_key(item: Any) -> str:
        for value in (getattr(item, "patent_id", None), getattr(item, "publication_number", None), getattr(item, "title", None)):
            text = str(value or "").strip().lower()
            if text:
                return text
        return f"session:{getattr(item, 'session_id', '')}:item:{getattr(item, 'item_id', 0)}"

    @staticmethod
    def _has_effective_analysis_text(text: str | None) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        lower = value.lower()
        if value.startswith("自动分析失败："):
            return False
        if lower.startswith("**error**") or lower.startswith("error:") or "llm_error_response" in lower:
            return False
        return True

    @staticmethod
    def _is_downloaded_status(status: str | None) -> bool:
        return download_common_utils.is_downloaded_status(status)

    @staticmethod
    def _is_true(value: Any) -> bool:
        return download_common_utils.is_truthy_flag(value)

    @staticmethod
    def parse_keywords(keyword_text: str) -> list[str]:
        return download_common_utils.parse_keywords(keyword_text)

    @staticmethod
    def _build_query(keywords: list[str], use_and: bool) -> str:
        return download_common_utils.build_query(keywords, use_and)

    @staticmethod
    def _contains_chinese(text: str) -> bool:
        return download_common_utils.contains_chinese(text)

    @staticmethod
    def _content_disposition(filename: str) -> str:
        return download_common_utils.build_content_disposition(filename)

    def _session_dir(self, *, actor_id: str, session_id: str) -> Path:
        return self._execution_manager.session_dir(
            root=self._download_root(),
            actor_id=actor_id,
            session_id=session_id,
        )

    def _download_pdf_bytes(self, url: str) -> bytes:
        return download_common_utils.download_pdf_bytes(url, user_agent=self._DOWNLOAD_USER_AGENT, timeout=45)

    @staticmethod
    def _strip_html(value: str | None) -> str:
        return download_common_utils.strip_html_text(value)

    @classmethod
    def _kb_target_candidates(cls, kb_ref: str, kb_info: Any) -> list[str]:
        raw = str(kb_ref or "").strip()
        bracket_inner = ""
        m = re.fullmatch(r"\[(.+)\]", raw)
        if m:
            bracket_inner = str(m.group(1) or "").strip()
        ordered: list[str] = []
        for value in (
            getattr(kb_info, "dataset_id", None),
            getattr(kb_info, "name", None),
            raw,
            bracket_inner,
        ):
            text = str(value or "").strip()
            if text and text not in ordered:
                ordered.append(text)
        return ordered

    @staticmethod
    def _normalize_match_text(value: str | None) -> str:
        return download_common_utils.normalize_match_text(value)

    @staticmethod
    def _translator_script_path() -> Path:
        return download_common_utils.translator_script_path()

    @staticmethod
    def _parse_translator_output(stdout: str) -> str:
        return download_common_utils.parse_translator_output(stdout)

    def _translate_query_for_uspto(self, query: str) -> str:
        return download_common_utils.translate_query_for_uspto(
            query,
            script_path=self._translator_script_path(),
            timeout=30,
        )

    @staticmethod
    def _extract_completion_answer(payload: dict[str, Any] | None) -> str:
        return LLMAnalysisManager.extract_completion_answer(payload)

    @staticmethod
    def _is_chat_method_unsupported_error(text: str) -> bool:
        return LLMAnalysisManager.is_chat_method_unsupported_error(text)

    def _resolve_general_llm_chat_ids(self) -> list[str]:
        return self._llm_manager.resolve_general_llm_chat_ids()

    def _get_or_create_llm_session(
        self,
        *,
        actor: str,
        chat_id: str,
        force_new: bool = False,
        session_name: str | None = None,
    ) -> str:
        return self._llm_manager.get_or_create_session(
            actor=actor,
            chat_id=chat_id,
            force_new=force_new,
            session_name=session_name,
        )

    def _ask_general_llm(self, *, actor: str, question: str, per_item_session_tag: str | None = None) -> str:
        return self._llm_manager.ask(actor=actor, question=question, per_item_session_tag=per_item_session_tag)

    def _run_item_auto_analysis(self, *, actor: str, item: Any) -> tuple[str | None, str | None]:
        if not self._is_downloaded_status(getattr(item, "status", None)):
            return None, None
        if not str(getattr(item, "file_path", "") or "").strip():
            return None, None
        question = self._build_analysis_prompt(item=item)
        analysis_text = self._ask_general_llm(
            actor=actor,
            question=question,
            per_item_session_tag=f"s{getattr(item, 'session_id', '')}-i{getattr(item, 'item_id', 0)}",
        )
        txt_path = self._analysis_txt_path(item=item)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(analysis_text, encoding="utf-8")
        return analysis_text, str(txt_path)

    @staticmethod
    def _analysis_failure_text(error: Exception) -> str:
        return f"auto_analyze_failed: {error}"

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        data = self._item_to_dict(item)
        path = str(data.pop("file_path", "") or "")
        data["has_file"] = bool(path and Path(path).exists())
        analysis_path = str(data.get("analysis_file_path") or "")
        data["has_analysis_file"] = bool(analysis_path and Path(analysis_path).exists())
        data["downloaded_before"] = str(data.get("status") or "") == "downloaded_cached"
        return data

    def _register_job(self, session_id: str, job: Any) -> None:
        self._execution_manager.register_job(session_id=session_id, job=job)

    def _cancel_job(self, session_id: str) -> Any:
        return self._execution_manager.cancel_job(session_id=session_id)

    def _is_cancelled(self, session_id: str) -> bool:
        return self._execution_manager.is_cancelled(session_id=session_id)

    def _request_stop(self, session_id: str) -> Any:
        return self._execution_manager.request_stop(session_id=session_id)

    def _is_stop_requested(self, session_id: str) -> bool:
        return self._execution_manager.is_stop_requested(session_id=session_id)

    def _finish_job(self, session_id: str) -> None:
        self._execution_manager.finish_job(session_id=session_id)

    def _session_not_found_detail(self) -> str:
        return f"{self._DM_KIND}_session_not_found"

    def _session_not_allowed_detail(self) -> str:
        return f"{self._DM_KIND}_session_not_allowed"

    def _item_not_found_detail(self) -> str:
        return f"{self._DM_KIND}_item_not_found"

    def _file_not_found_detail(self, filename: str | None) -> str:
        return f"{self._DM_KIND}_file_not_found: {filename or ''}"

    def _file_read_failed_detail(self, error: Exception) -> str:
        return f"{self._DM_KIND}_file_read_failed: {error}"

    def _add_to_kb_failed_prefix(self) -> str:
        return f"{self._DM_KIND}_add_to_kb_failed:"

    def _assert_session_access(self, session: Any, ctx: Any) -> None:
        if bool(getattr(ctx.snapshot, "is_admin", False)):
            return
        if str(getattr(session, "created_by", "")) != str(ctx.payload.sub):
            raise HTTPException(status_code=403, detail=self._session_not_allowed_detail())

    def _resolve_session_and_item(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[Any, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=self._session_not_found_detail())
        self._assert_session_access(session, ctx)
        item = self.store.get_item(session_id=session_id, item_id=item_id)
        if not item:
            raise HTTPException(status_code=404, detail=self._item_not_found_detail())
        return session, item

    def _ensure_file_bytes(self, *, file_path: str | None, filename: str | None) -> bytes:
        path = Path(str(file_path or ""))
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail=self._file_not_found_detail(filename))
        try:
            return path.read_bytes()
        except Exception as e:
            raise HTTPException(status_code=500, detail=self._file_read_failed_detail(e)) from e

    def stop_session_download(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=self._session_not_found_detail())
        self._assert_session_access(session, ctx)

        status = str(getattr(session, "status", "") or "")
        if status in {"completed", "failed", "stopped"}:
            return {"ok": True, "already_finished": True, "status": status, "session_id": session_id}

        job = self._request_stop(session_id)
        if job is not None and job.is_alive():
            self.store.update_session_runtime(session_id=session_id, status="stopping")
            return {"ok": True, "already_finished": False, "status": "stopping", "session_id": session_id}

        self.store.update_session_runtime(session_id=session_id, status="stopped")
        return {"ok": True, "already_finished": False, "status": "stopped", "session_id": session_id}

    @classmethod
    def _build_summary(cls, items: list[Any], status: str | None) -> dict[str, Any]:
        return {
            "status": str(status or ""),
            "total": len(items),
            "downloaded": sum(1 for i in items if cls._is_downloaded_status(getattr(i, "status", None))),
            "failed": sum(1 for i in items if not cls._is_downloaded_status(getattr(i, "status", None))),
            "added": sum(1 for i in items if bool(getattr(i, "added_doc_id", None))),
            "analyzed": sum(1 for i in items if bool(getattr(i, "analysis_text", None))),
        }

    def get_session_payload(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=self._session_not_found_detail())
        self._assert_session_access(session, ctx)
        items = self.store.list_items(session_id=session_id)
        session_data = self._session_to_dict(session)
        return {
            "session": session_data,
            "items": [self._serialize_item(i) for i in items],
            "source_errors": session_data.get("source_errors") or {},
            "source_stats": session_data.get("source_stats") or {},
            "summary": self._build_summary(items, getattr(session, "status", "")),
        }

    def list_history_keywords(self, *, ctx: Any) -> dict[str, Any]:
        return self._history_manager.list_history_keywords(ctx=ctx)

    def get_history_group_payload(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        return self._history_manager.get_history_group_payload(history_key=history_key, ctx=ctx)

    def delete_history_group(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        return self._history_manager.delete_history_group(history_key=history_key, ctx=ctx)

    def add_history_group_to_local_kb(self, *, history_key: str, ctx: Any, kb_ref: str | None = None) -> dict[str, Any]:
        return self._history_manager.add_history_group_to_local_kb(
            history_key=history_key,
            ctx=ctx,
            kb_ref=(kb_ref or self._DM_DEFAULT_LOCAL_KB_REF),
        )

    def get_item_preview_payload(self, *, session_id: str, item_id: int, ctx: Any, render: str = "default") -> dict[str, Any]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        filename = item.filename or f"{self._DM_DEFAULT_FILENAME_PREFIX}_{item_id}.pdf"
        return build_preview_payload(content, filename, doc_id=str(item_id), render=render)

    def get_item_download_payload(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[bytes, str, str]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        filename = item.filename or f"{self._DM_DEFAULT_FILENAME_PREFIX}_{item_id}.pdf"
        mime_type = item.mime_type or self._MIME_TYPE_DEFAULT
        return content, filename, mime_type

    def _upload_blob_to_kb(
        self,
        *,
        ctx: Any,
        kb_ref: str,
        filename: str,
        content: bytes,
        mime_type: str,
        review_notes: str,
    ) -> Any:
        deps = self.deps
        kb_info = resolve_kb_ref(deps, kb_ref)
        uploads_dir = resolve_repo_path(settings.UPLOAD_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        staged_filename = f"{uuid.uuid4()}_{filename}"
        staged_path = uploads_dir / staged_filename
        staged_path.write_bytes(content)

        doc = None
        try:
            doc = deps.kb_store.create_document(
                filename=filename,
                file_path=str(staged_path),
                file_size=len(content),
                mime_type=mime_type,
                uploaded_by=ctx.payload.sub,
                kb_id=(kb_info.dataset_id or kb_ref),
                kb_dataset_id=kb_info.dataset_id,
                kb_name=(kb_info.name or kb_ref),
                status="pending",
            )

            kb_targets = self._kb_target_candidates(kb_ref, kb_info)
            ragflow_doc_id = None
            selected_target = None
            for target in kb_targets:
                try:
                    ragflow_doc_id = deps.ragflow_service.upload_document_blob(
                        file_filename=doc.filename,
                        file_content=content,
                        kb_id=target,
                    )
                except Exception:
                    ragflow_doc_id = None
                if ragflow_doc_id:
                    selected_target = target
                    break
            if not ragflow_doc_id:
                raise HTTPException(
                    status_code=502,
                    detail=f"upload_to_ragflow_failed: kb_ref={kb_ref}, targets={','.join(kb_targets)}",
                )

            selected_kb_info = resolve_kb_ref(deps, selected_target or kb_ref)
            dataset_ref = selected_kb_info.dataset_id or selected_target or kb_ref
            if ragflow_doc_id != "uploaded":
                try:
                    deps.ragflow_service.parse_document(dataset_ref=dataset_ref, document_id=ragflow_doc_id)
                except Exception:
                    pass

            updated = deps.kb_store.update_document_status(
                doc_id=doc.doc_id,
                status="approved",
                reviewed_by=ctx.payload.sub,
                review_notes=review_notes,
                ragflow_doc_id=ragflow_doc_id,
            )
            if not updated:
                raise RuntimeError("kb_status_update_failed")
            return updated
        except Exception:
            if doc is not None:
                try:
                    deps.kb_store.delete_document(doc.doc_id)
                except Exception:
                    pass
            try:
                if staged_path.exists():
                    staged_path.unlink()
            except Exception:
                pass
            raise

    def add_item_to_local_kb(
        self,
        *,
        session_id: str,
        item_id: int,
        ctx: Any,
        kb_ref: str | None = None,
        from_batch: bool = False,
    ) -> dict[str, Any]:
        resolved_kb_ref = kb_ref or self._DM_DEFAULT_LOCAL_KB_REF
        try:
            return self._kb_lifecycle_manager.add_item_to_local_kb(
                session_id=session_id,
                item_id=item_id,
                ctx=ctx,
                kb_ref=resolved_kb_ref,
                from_batch=from_batch,
                action_name=f"{self._DM_KIND}_kb_add",
                source_name=self._DM_SOURCE_NAME,
                entity_source_key=self._DM_ENTITY_SOURCE_KEY,
                entity_id_key=self._DM_ENTITY_ID_KEY,
                default_filename_prefix=self._DM_DEFAULT_FILENAME_PREFIX,
                add_review_notes=self._DM_ADD_REVIEW_NOTES,
                analysis_review_notes=self._DM_ANALYSIS_REVIEW_NOTES,
            )
        except Exception as e:
            prefix = self._add_to_kb_failed_prefix()
            if isinstance(e, HTTPException):
                if not str(e.detail).startswith(prefix):
                    raise HTTPException(status_code=e.status_code, detail=f"{prefix} {e.detail}") from e
                raise
            raise HTTPException(status_code=500, detail=f"{prefix} {e}") from e

    def add_all_to_local_kb(
        self,
        *,
        session_id: str,
        ctx: Any,
        kb_ref: str | None = None,
    ) -> dict[str, Any]:
        return self._kb_lifecycle_manager.add_all_to_local_kb(
            session_id=session_id,
            ctx=ctx,
            kb_ref=(kb_ref or self._DM_DEFAULT_LOCAL_KB_REF),
            session_not_found_detail=self._session_not_found_detail(),
            action_name=f"{self._DM_KIND}_kb_add_all",
            source_name=self._DM_SOURCE_NAME,
            item_add_fn=self.add_item_to_local_kb,
        )

    def delete_item(self, *, session_id: str, item_id: int, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        return self._kb_lifecycle_manager.delete_item(
            session_id=session_id,
            item_id=item_id,
            ctx=ctx,
            delete_local_kb=delete_local_kb,
            not_found_detail=self._item_not_found_detail(),
            action_name=f"{self._DM_KIND}_item_delete",
            source_name=self._DM_SOURCE_NAME,
        )

    def delete_session(self, *, session_id: str, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        return self._kb_lifecycle_manager.delete_session(
            session_id=session_id,
            ctx=ctx,
            delete_local_kb=delete_local_kb,
            session_not_found_detail=self._session_not_found_detail(),
            action_name=f"{self._DM_KIND}_session_delete",
            source_name=self._DM_SOURCE_NAME,
        )

    def content_disposition(self, filename: str) -> str:
        return self._content_disposition(filename)
