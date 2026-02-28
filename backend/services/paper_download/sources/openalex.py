from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from .base import PaperCandidate, PaperSourceError


class OpenAlexSource:
    SOURCE_KEY = "openalex"
    SOURCE_LABEL = "OpenAlex"
    _API_URL = "https://api.openalex.org/works"
    _USER_AGENT = "paper-download-openalex/1.0"
    _MAX_PAGE_SIZE = 200

    @classmethod
    def _request_json(cls, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, headers={"User-Agent": cls._USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            raise PaperSourceError(f"openalex_query_failed: {e}") from e
        try:
            payload = json.loads(raw)
        except Exception as e:
            raise PaperSourceError(f"openalex_query_invalid_json: {e}") from e
        if not isinstance(payload, dict):
            raise PaperSourceError("openalex_query_invalid_payload")
        return payload

    @staticmethod
    def _as_text(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _decode_abstract(cls, inverted_index: Any) -> str:
        if not isinstance(inverted_index, dict):
            return ""
        pos_to_word: dict[int, str] = {}
        for word, pos_list in inverted_index.items():
            if not isinstance(word, str) or not isinstance(pos_list, list):
                continue
            for pos in pos_list:
                if not isinstance(pos, int) or pos < 0:
                    continue
                if pos not in pos_to_word:
                    pos_to_word[pos] = word
        if not pos_to_word:
            return ""
        ordered = [pos_to_word[i] for i in sorted(pos_to_word.keys())]
        return " ".join(ordered)

    @classmethod
    def _paper_id(cls, row: dict[str, Any]) -> str:
        work_id = cls._as_text(row.get("id"))
        if work_id:
            return work_id.rsplit("/", 1)[-1]
        doi = cls._as_text(row.get("doi"))
        return doi.rsplit("/", 1)[-1] if doi else ""

    @classmethod
    def _publication_number(cls, row: dict[str, Any]) -> str:
        doi = cls._as_text(row.get("doi"))
        if doi:
            if doi.lower().startswith("https://doi.org/"):
                return doi[16:]
            return doi
        return cls._paper_id(row)

    @classmethod
    def _authors_text(cls, row: dict[str, Any]) -> str:
        authorships = row.get("authorships")
        if not isinstance(authorships, list):
            return ""
        names: list[str] = []
        for author_item in authorships:
            if not isinstance(author_item, dict):
                continue
            author = author_item.get("author")
            if not isinstance(author, dict):
                continue
            name = cls._as_text(author.get("display_name"))
            if name:
                names.append(name)
            if len(names) >= 20:
                break
        return ", ".join(names)

    @classmethod
    def _assignee_text(cls, row: dict[str, Any]) -> str:
        primary_location = row.get("primary_location")
        if isinstance(primary_location, dict):
            source = primary_location.get("source")
            if isinstance(source, dict):
                display_name = cls._as_text(source.get("display_name"))
                if display_name:
                    return display_name
        host_venue = row.get("host_venue")
        if isinstance(host_venue, dict):
            display_name = cls._as_text(host_venue.get("display_name"))
            if display_name:
                return display_name
        return ""

    @classmethod
    def _detail_url(cls, row: dict[str, Any]) -> str:
        best_oa = row.get("best_oa_location")
        if isinstance(best_oa, dict):
            landing = cls._as_text(best_oa.get("landing_page_url"))
            if landing:
                return landing
        primary_location = row.get("primary_location")
        if isinstance(primary_location, dict):
            landing = cls._as_text(primary_location.get("landing_page_url"))
            if landing:
                return landing
        return cls._as_text(row.get("id"))

    @classmethod
    def _pdf_url(cls, row: dict[str, Any]) -> str:
        best_oa = row.get("best_oa_location")
        if isinstance(best_oa, dict):
            pdf = cls._as_text(best_oa.get("pdf_url"))
            if pdf:
                return pdf
        primary_location = row.get("primary_location")
        if isinstance(primary_location, dict):
            pdf = cls._as_text(primary_location.get("pdf_url"))
            if pdf:
                return pdf
        open_access = row.get("open_access")
        if isinstance(open_access, dict):
            oa_url = cls._as_text(open_access.get("oa_url"))
            if oa_url and (oa_url.lower().endswith(".pdf") or "/pdf" in oa_url.lower()):
                return oa_url
        return ""

    @classmethod
    def _to_candidate(cls, row: dict[str, Any]) -> PaperCandidate:
        title = cls._as_text(row.get("display_name"))
        abstract_text = cls._decode_abstract(row.get("abstract_inverted_index"))
        if not abstract_text:
            abstract_text = cls._as_text(row.get("abstract"))
        publication_number = cls._publication_number(row)
        paper_id = cls._paper_id(row) or publication_number or title
        publication_date = cls._as_text(row.get("publication_date")) or cls._as_text(row.get("publication_year"))
        inventor = cls._authors_text(row)
        assignee = cls._assignee_text(row)
        detail_url = cls._detail_url(row)
        pdf_url = cls._pdf_url(row)

        return PaperCandidate(
            source=cls.SOURCE_KEY,
            source_label=cls.SOURCE_LABEL,
            patent_id=paper_id,
            title=title or publication_number or "(untitled paper)",
            abstract_text=abstract_text,
            publication_number=publication_number,
            publication_date=publication_date,
            inventor=inventor,
            assignee=assignee,
            detail_url=detail_url,
            pdf_url=(pdf_url or None),
        )

    def search(self, *, query: str, limit: int) -> list[PaperCandidate]:
        q = str(query or "").strip()
        if not q:
            return []

        lim = max(1, min(int(limit), 1000))
        page = 1
        out: list[PaperCandidate] = []

        while len(out) < lim:
            page_size = min(self._MAX_PAGE_SIZE, lim - len(out))
            params = {
                "search": q,
                "per-page": page_size,
                "page": page,
            }
            url = f"{self._API_URL}?{urllib.parse.urlencode(params)}"
            payload = self._request_json(url)
            rows = payload.get("results")
            if not isinstance(rows, list) or not rows:
                break

            for row in rows:
                if not isinstance(row, dict):
                    continue
                out.append(self._to_candidate(row))
                if len(out) >= lim:
                    break

            if len(rows) < page_size:
                break
            page += 1

        return out
