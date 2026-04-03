from __future__ import annotations

from datetime import datetime
from typing import Any


_PURPOSE_LABELS = {
    "preview": "预览",
    "download": "下载",
    "batch_download": "批量下载",
}


class DocumentWatermarkService:
    def __init__(self, *, store: Any, org_directory_store: Any = None):
        if store is None:
            raise RuntimeError("watermark_policy_store_unavailable")
        self._store = store
        self._org_directory_store = org_directory_store

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
        username = self._resolve_username(user=user, payload_sub=payload_sub)
        company_name = self._resolve_company_name(user=user)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        purpose_label = _PURPOSE_LABELS.get(str(purpose or "").strip().lower(), str(purpose or "").strip() or "未知")

        try:
            watermark_text = str(
                policy.text_template.format(
                    username=username,
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
            "username": username,
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

    def _resolve_company_name(self, *, user: Any) -> str:
        company_id = getattr(user, "company_id", None)
        if company_id is None:
            return "未配置公司"
        if self._org_directory_store is None:
            raise RuntimeError("org_directory_store_unavailable")
        company = self._org_directory_store.get_company(int(company_id))
        if company is None:
            return f"公司ID:{int(company_id)}"
        value = str(getattr(company, "name", "") or "").strip()
        return value or f"公司ID:{int(company_id)}"
