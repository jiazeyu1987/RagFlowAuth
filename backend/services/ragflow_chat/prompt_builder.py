from typing import Any, Dict
import re


PARSED_FILE_FIELD_PATTERN = re.compile(r"parsed.*file|file.*parsed", re.IGNORECASE)


class RagflowPromptBuilder:
    def _sanitize_chat_payload(self, payload: dict[str, Any], *, for_update: bool) -> dict[str, Any]:
        """
        RAGFlow APIs tend to reject read-only fields (id/tenant/time/status).
        We keep the contract flexible (frontend edits JSON), but strip obvious
        server-managed fields before calling RAGFlow create/update endpoints.
        """
        body: dict[str, Any] = dict(payload or {})

        # Path params control identity; never allow client to override.
        body.pop("id", None)
        body.pop("chat_id", None)

        # Common read-only / computed fields observed in RAGFlow payloads.
        for k in [
            "tenant_id",
            "create_time",
            "update_time",
            "status",
            "token_num",
            "document_count",
            "chunk_count",
        ]:
            body.pop(k, None)

        # Some deployments include task metadata; strip by default.
        for k in list(body.keys()):
            if not isinstance(k, str):
                continue
            if k.endswith("_task_id") or k.endswith("_task_finish_at") or k.endswith("_task_start_at"):
                body.pop(k, None)
                continue
            if PARSED_FILE_FIELD_PATTERN.search(k):
                body.pop(k, None)

        # Update: keep only provided fields (caller may send full object though).
        # Create: allow a full config blob, but caller should ensure required fields exist.
        if for_update:
            # Ensure we don't accidentally send empty updates that would confuse upstream.
            return body
        return body

    @staticmethod
    def _extract_dataset_ids(payload: dict[str, Any]) -> list[str]:
        if not isinstance(payload, dict):
            return []

        raw = payload.get("dataset_ids")
        if isinstance(raw, list):
            out = []
            for x in raw:
                s = str(x or "").strip()
                if s:
                    out.append(s)
            if out:
                return out

        raw = payload.get("kb_ids")
        if isinstance(raw, list):
            out = []
            for x in raw:
                s = str(x or "").strip()
                if s:
                    out.append(s)
            if out:
                return out

        ds = payload.get("datasets")
        if isinstance(ds, list):
            out = []
            for item in ds:
                if item is None:
                    continue
                if isinstance(item, (str, int, float)):
                    s = str(item).strip()
                    if s:
                        out.append(s)
                    continue
                if isinstance(item, dict):
                    raw_id = item.get("id") or item.get("dataset_id") or item.get("kb_id") or item.get("datasetId") or item.get("kbId")
                    s = str(raw_id or "").strip()
                    if s:
                        out.append(s)
            return out

        return []

    @staticmethod
    def _parsed_file_clear_fields(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Detect parsed-file binding fields in a chat payload and compute "empty" values.

        RAGFlow versions differ, but the ownership error string indicates there are hidden bindings
        from chat -> parsed files. If present, they typically contain both "parsed" and "file".
        """
        if not isinstance(payload, dict):
            return {}
        fields: dict[str, Any] = {}
        for k, v in payload.items():
            if not isinstance(k, str):
                continue
            if not PARSED_FILE_FIELD_PATTERN.search(k):
                continue
            # Only clear fields that already exist on this RAGFlow version.
            # Keep the "shape" so the remote validation is more likely to accept it.
            if isinstance(v, list):
                fields[k] = []
            elif isinstance(v, str):
                fields[k] = ""
        return fields

    @staticmethod
    def default_agent_dsl() -> Dict[str, Any]:
        """
        Minimal DSL payload required by RAGFlow when creating an agent.

        Note: Always return a new dict to avoid accidental cross-request mutation.
        """
        return {
            "components": {
                "begin": {
                    "downstream": [],
                    "obj": {"component_name": "Begin", "params": {}},
                    "upstream": [],
                }
            },
            "globals": {
                "sys.conversation_turns": 0,
                "sys.files": [],
                "sys.query": "",
                "sys.user_id": "",
            },
            "graph": {
                "edges": [],
                "nodes": [
                    {
                        "data": {"label": "Begin", "name": "begin"},
                        "id": "begin",
                        "position": {"x": 50, "y": 200},
                        "sourcePosition": "left",
                        "targetPosition": "right",
                        "type": "beginNode",
                    }
                ],
            },
            "history": [],
            "path": [],
            "retrieval": [],
        }
