from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.services.org_directory_store import OrgDirectoryStore


_PURPOSE_LABELS = {
    "preview": "预览",
    "download": "下载",
    "batch_download": "批量下载",
}


class DocumentWatermarkService:
    def __init__(
        self,
        *,
        store: Any,
        org_structure_manager: Any = None,
        global_org_directory_store: Any = None,
    ):
        if store is None:
            raise RuntimeError("watermark_policy_store_unavailable")
        self._store = store
        self._org_structure_manager = org_structure_manager
        self._global_org_directory_store = global_org_directory_store

    def build_watermark(
        self,
        *,
        user: Any,
        payload_sub: str | None,
        purpose: str,
        doc_id: str,
        filename: str | None,
        source: str,
    ) -> dict[str, Any]:
        policy = self._store.get_active_policy()
        actor_name = self._resolve_username(user=user, payload_sub=payload_sub)
        actor_account = self._resolve_user_account(user=user, payload_sub=payload_sub)
        company_name = self._resolve_company_name(user=user)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        purpose_label = _PURPOSE_LABELS.get(str(purpose or "").strip().lower(), str(purpose or "").strip() or "未知")

        try:
            watermark_text = str(
                policy.text_template.format(
                    username=actor_name,
                    company=company_name,
                    timestamp=timestamp,
                    purpose=purpose_label,
                    doc_id=str(doc_id or "").strip(),
                    filename=str(filename or "").strip(),
                    source=str(source or "").strip(),
                )
            )
        except Exception as exc:
            raise RuntimeError(f"watermark_template_render_failed:{exc}") from exc

        return {
            "policy_id": policy.policy_id,
            "policy_name": policy.name,
            "purpose": str(purpose or "").strip().lower(),
            "purpose_label": purpose_label,
            "label": policy.label_text or "受控预览",
            "text": watermark_text,
            "username": actor_name,
            "actor_name": actor_name,
            "actor_account": actor_account,
            "company": company_name,
            "timestamp": timestamp,
            "doc_id": str(doc_id or "").strip(),
            "filename": str(filename or "").strip(),
            "source": str(source or "").strip(),
            "overlay": {
                "text_color": policy.text_color or "#6b7280",
                "opacity": float(policy.opacity),
                "rotation_deg": int(policy.rotation_deg),
                "gap_x": int(policy.gap_x),
                "gap_y": int(policy.gap_y),
                "font_size": int(policy.font_size),
            },
        }

    def build_distribution_note(
        self,
        *,
        watermark: dict[str, Any],
        filename: str,
        source: str,
        item_count: int | None = None,
    ) -> str:
        lines = [
            "受控分发说明",
            "本次导出包含可追溯水印信息，请勿截图、转发或二次分发。",
            f"水印策略: {watermark.get('policy_name') or watermark.get('policy_id')}",
            f"水印内容: {watermark.get('text')}",
            f"来源: {source}",
            f"文件: {filename}",
        ]
        if item_count is not None:
            lines.append(f"文件数量: {int(item_count)}")
        return "\n".join(lines) + "\n"

    def build_manifest(
        self,
        *,
        watermark: dict[str, Any],
        source: str,
        filename: str,
        documents: list[dict[str, Any]] | None = None,
        distribution_mode: str,
    ) -> dict[str, Any]:
        return {
            "distribution_mode": distribution_mode,
            "source": str(source or "").strip(),
            "filename": str(filename or "").strip(),
            "watermark_policy_id": watermark.get("policy_id"),
            "watermark_policy_name": watermark.get("policy_name"),
            "watermark_text": watermark.get("text"),
            "purpose": watermark.get("purpose"),
            "purpose_label": watermark.get("purpose_label"),
            "username": watermark.get("username"),
            "company": watermark.get("company"),
            "timestamp": watermark.get("timestamp"),
            "doc_id": watermark.get("doc_id"),
            "documents": list(documents or []),
        }

    @staticmethod
    def _resolve_username(*, user: Any, payload_sub: str | None) -> str:
        value = str(
            getattr(user, "full_name", None)
            or getattr(user, "username", None)
            or payload_sub
            or ""
        ).strip()
        if not value:
            raise RuntimeError("watermark_actor_missing")
        return value

    @staticmethod
    def _resolve_user_account(*, user: Any, payload_sub: str | None) -> str:
        value = str(
            getattr(user, "username", None)
            or payload_sub
            or ""
        ).strip()
        if not value:
            raise RuntimeError("watermark_actor_account_missing")
        return value

    def _resolve_company_name(self, *, user: Any) -> str:
        direct_name = self._normalize_company_name(getattr(user, "company_name", None))
        if direct_name:
            return direct_name
        company_id = getattr(user, "company_id", None)
        if company_id is None:
            return "未配置公司"
        try:
            normalized_company_id = int(company_id)
        except Exception:
            return "未配置公司"
        company = self._resolve_company(normalized_company_id)
        if company is None:
            return "未配置公司"
        value = self._normalize_company_name(getattr(company, "name", None))
        return value or "未配置公司"

    def _resolve_company(self, company_id: int) -> Any:
        for resolver in (self._org_structure_manager, self._get_global_org_directory_store()):
            if resolver is None:
                continue
            company = resolver.get_company(company_id)
            if company is None:
                continue
            if self._normalize_company_name(getattr(company, "name", None)):
                return company
        return None

    def _get_global_org_directory_store(self) -> Any:
        if self._global_org_directory_store is None:
            self._global_org_directory_store = OrgDirectoryStore(db_path=str(resolve_auth_db_path()))
        return self._global_org_directory_store

    @staticmethod
    def _normalize_company_name(value: Any) -> str:
        return str(value or "").strip()
