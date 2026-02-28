from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import PatentCandidate, PatentSourceError


class UsptoSource:
    SOURCE_KEY = "uspto"
    SOURCE_LABEL = "USPTO"

    _API_BASE = "https://ppubs.uspto.gov/api"
    _SESSION_URL = f"{_API_BASE}/users/me/session"
    _SEARCH_URL = f"{_API_BASE}/searches/generic"
    _PDF_URL = f"{_API_BASE}/pdf/downloadPdf"
    _USER_AGENT = "uspto-source/1.0"
    _MAX_SCAN = 5000

    def __init__(self, _google_source=None):
        # Keep constructor compatibility with existing manager wiring.
        self._google_source = _google_source

    def _request_session_token(self) -> str:
        req = urllib.request.Request(
            self._SESSION_URL,
            method="POST",
            data=b"-1",
            headers={"User-Agent": self._USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                token = str(resp.headers.get("x-access-token", "") or "").strip()
        except Exception as e:
            raise PatentSourceError(f"uspto_session_failed: {e}") from e
        if not token:
            raise PatentSourceError("uspto_session_missing_token")
        return token

    @staticmethod
    def _guess_op(query: str) -> str:
        q = str(query or "").upper()
        if " OR " in q:
            return "OR"
        return "AND"

    @staticmethod
    def _doc_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return ", ".join([str(x).strip() for x in value if str(x).strip()])
        if isinstance(value, dict):
            # Common structures in USPTO responses can nest name fields.
            for key in ("name", "value", "text"):
                if key in value:
                    return str(value.get(key) or "").strip()
            return str(value).strip()
        return str(value).strip()

    @classmethod
    def _extract_patent_number(cls, doc: dict) -> str:
        for key in ("patentNumber", "documentId", "publicationNumber", "patent_number"):
            v = cls._doc_text(doc.get(key))
            if v:
                return v.replace(" ", "")
        return ""

    def _search_docs(self, *, query: str, limit: int, token: str) -> list[dict]:
        docs: list[dict] = []
        cursor_marker = "*"
        scanned = 0
        op = self._guess_op(query)
        page_size = min(100, max(50, int(limit)))

        while len(docs) < int(limit) and scanned < self._MAX_SCAN:
            payload = {
                "cursorMarker": cursor_marker,
                "databaseFilters": [
                    {"databaseName": "USPAT"},
                    {"databaseName": "US-PGPUB"},
                    {"databaseName": "USOCR"},
                ],
                "fields": [
                    "documentId",
                    "patentNumber",
                    "title",
                    "datePublished",
                    "inventors",
                    "assignees",
                    "pageCount",
                    "type",
                ],
                "op": op,
                "pageSize": page_size,
                "q": str(query or "").strip(),
                "searchType": 0,
                "sort": "date_publ desc",
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._SEARCH_URL,
                method="POST",
                data=body,
                headers={
                    "User-Agent": self._USER_AGENT,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "x-access-token": token,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result = json.loads(resp.read().decode("utf-8", errors="ignore"))
            except Exception as e:
                raise PatentSourceError(f"uspto_search_failed: {e}") from e

            page_docs = result.get("docs", []) if isinstance(result, dict) else []
            if not isinstance(page_docs, list) or not page_docs:
                break

            scanned += len(page_docs)
            docs.extend(page_docs)

            next_cursor = result.get("cursorMarker") if isinstance(result, dict) else None
            if not next_cursor or next_cursor == cursor_marker:
                break
            cursor_marker = str(next_cursor)

        return docs[: int(limit)]

    def _build_pdf_url(self, patent_number: str, token: str) -> str:
        encoded_number = urllib.parse.quote(str(patent_number or ""))
        encoded_token = urllib.parse.quote(str(token or ""), safe="")
        return f"{self._PDF_URL}/{encoded_number}?requestToken={encoded_token}"

    def _build_detail_url(self, patent_number: str) -> str:
        num = urllib.parse.quote(str(patent_number or ""))
        return f"https://ppubs.uspto.gov/pubwebapp/static/pages/ppubsbasic.html?patentNumber={num}"

    def search(self, *, query: str, limit: int) -> list[PatentCandidate]:
        q = str(query or "").strip()
        if not q:
            return []
        lim = max(1, min(int(limit), 1000))
        token = self._request_session_token()
        raw_docs = self._search_docs(query=q, limit=lim, token=token)

        rows: list[PatentCandidate] = []
        seen: set[str] = set()
        for doc in raw_docs:
            if not isinstance(doc, dict):
                continue
            patent_number = self._extract_patent_number(doc)
            if not patent_number:
                continue
            key = patent_number.upper()
            if key in seen:
                continue
            seen.add(key)

            title = self._doc_text(doc.get("title")) or patent_number
            inventors = self._doc_text(doc.get("inventors"))
            assignees = self._doc_text(doc.get("assignees"))
            pub_date = self._doc_text(doc.get("datePublished"))

            rows.append(
                PatentCandidate(
                    source=self.SOURCE_KEY,
                    source_label=self.SOURCE_LABEL,
                    patent_id=patent_number,
                    title=title,
                    abstract_text="",
                    publication_number=patent_number,
                    publication_date=pub_date,
                    inventor=inventors,
                    assignee=assignees,
                    detail_url=self._build_detail_url(patent_number),
                    pdf_url=self._build_pdf_url(patent_number, token),
                )
            )
            if len(rows) >= lim:
                break
        return rows
