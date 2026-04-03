from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Any

from backend.app.core.config import settings


class EmailNotificationAdapter:
    def send(
        self,
        *,
        channel: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        recipient: dict[str, Any] | None = None,
    ) -> None:
        config = channel.get("config") or {}

        host = str(config.get("host") or settings.SMTP_HOST or "").strip()
        if not host:
            raise RuntimeError("smtp_host_required")

        port = int(config.get("port") or settings.SMTP_PORT or 587)
        username = str(config.get("username") or settings.SMTP_USERNAME or "").strip()
        password = str(config.get("password") or settings.SMTP_PASSWORD or "")
        use_tls = bool(config.get("use_tls", settings.SMTP_USE_TLS))
        from_email = str(config.get("from_email") or settings.SMTP_FROM_EMAIL or "").strip()
        if not from_email:
            raise RuntimeError("smtp_from_email_required")

        recipient_email = str((recipient or {}).get("address") or "").strip()
        if not recipient_email:
            raise RuntimeError("smtp_to_email_required")

        msg = EmailMessage()
        msg["From"] = from_email
        msg["To"] = recipient_email
        msg["Subject"] = self._subject(event_type=event_type, payload=payload)
        msg.set_content(self._body(event_type=event_type, payload=payload, recipient=recipient))

        with smtplib.SMTP(host=host, port=port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(msg)

    @staticmethod
    def _subject(*, event_type: str, payload: dict[str, Any]) -> str:
        filename = str(payload.get("filename") or "").strip()
        current_step_name = str(payload.get("current_step_name") or "").strip()
        doc_id = str(payload.get("doc_id") or "").strip() or "unknown_document"
        if event_type == "review_todo_approval":
            return f"[RagflowAuth] Pending approval: {filename or doc_id} / {current_step_name or 'step'}"
        if event_type == "review_approved":
            return f"[RagflowAuth] Approved: {filename or doc_id}"
        if event_type == "review_rejected":
            return f"[RagflowAuth] Rejected: {filename or doc_id}"
        return f"[RagflowAuth] {event_type}: {filename or doc_id}"

    @staticmethod
    def _body(*, event_type: str, payload: dict[str, Any], recipient: dict[str, Any] | None) -> str:
        approval_target = payload.get("approval_target") or {}
        return "\n".join(
            [
                f"event_type: {event_type}",
                f"document: {payload.get('filename') or payload.get('doc_id') or ''}",
                f"step: {payload.get('current_step_name') or ''}",
                f"approval_path: {approval_target.get('route_path') or ''}",
                f"recipient: {(recipient or {}).get('username') or (recipient or {}).get('user_id') or ''}",
                "",
                "payload:",
                json.dumps(payload or {}, ensure_ascii=False, indent=2, sort_keys=True),
            ]
        )
