from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from .base import PaperCandidate, PaperSourceError


class _EuropePmcMixin:
    _API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    _USER_AGENT = "paper-download-europepmc/1.0"

    SOURCE_KEY = ""
    SOURCE_LABEL = ""

    def _build_query(self, query: str) -> str:
        return str(query or "").strip()

    def _prefer_pubmed_detail(self) -> bool:
        return False

    @classmethod
    def _request_json(cls, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, headers={"User-Agent": cls._USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            raise PaperSourceError(f"europe_pmc_query_failed: {e}") from e
        try:
            payload = json.loads(raw)
        except Exception as e:
            raise PaperSourceError(f"europe_pmc_query_invalid_json: {e}") from e
        if not isinstance(payload, dict):
            raise PaperSourceError("europe_pmc_query_invalid_payload")
        return payload

    @staticmethod
    def _as_text(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _article_pdf_url(cls, record: dict[str, Any]) -> str:
        pmcid = cls._as_text(record.get("pmcid"))
        has_pdf = cls._as_text(record.get("hasPDF")).upper() == "Y"
        record_id = cls._as_text(record.get("id"))
        if has_pdf and pmcid:
            return f"https://europepmc.org/articles/{pmcid}?pdf=render"
        if has_pdf and record_id.upper().startswith("PMC"):
            return f"https://europepmc.org/articles/{record_id}?pdf=render"

        full_text = record.get("fullTextUrlList")
        if isinstance(full_text, dict):
            urls = full_text.get("fullTextUrl")
            if isinstance(urls, list):
                for entry in urls:
                    if not isinstance(entry, dict):
                        continue
                    url = cls._as_text(entry.get("url"))
                    style = cls._as_text(entry.get("documentStyle")).lower()
                    if not url:
                        continue
                    if style == "pdf" or url.lower().endswith(".pdf"):
                        return url
        return ""

    @classmethod
    def _detail_url(cls, record: dict[str, Any], *, prefer_pubmed_detail: bool) -> str:
        pmid = cls._as_text(record.get("pmid"))
        record_id = cls._as_text(record.get("id"))
        source = cls._as_text(record.get("source"))
        if prefer_pubmed_detail and pmid:
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        if source and record_id:
            return f"https://europepmc.org/article/{source}/{record_id}"
        if pmid:
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        return ""

    @classmethod
    def _to_candidate(cls, *, record: dict[str, Any], source_key: str, source_label: str, prefer_pubmed_detail: bool) -> PaperCandidate:
        if not isinstance(record, dict):
            raise PaperSourceError("europe_pmc_invalid_record")

        record_id = cls._as_text(record.get("id"))
        pmid = cls._as_text(record.get("pmid"))
        doi = cls._as_text(record.get("doi"))
        title = cls._as_text(record.get("title"))
        publication_date = cls._as_text(record.get("firstPublicationDate")) or cls._as_text(record.get("pubYear"))
        author = cls._as_text(record.get("authorString"))
        journal = cls._as_text(record.get("journalTitle"))
        abstract_text = cls._as_text(record.get("abstractText"))
        publication_number = doi or pmid or record_id
        paper_id = pmid or record_id or publication_number or title
        detail_url = cls._detail_url(record, prefer_pubmed_detail=prefer_pubmed_detail)
        pdf_url = cls._article_pdf_url(record)

        return PaperCandidate(
            source=source_key,
            source_label=source_label,
            patent_id=paper_id,
            title=title or publication_number or "(untitled paper)",
            abstract_text=abstract_text,
            publication_number=publication_number,
            publication_date=publication_date,
            inventor=author,
            assignee=journal,
            detail_url=detail_url,
            pdf_url=(pdf_url or None),
        )

    def search(self, *, query: str, limit: int) -> list[PaperCandidate]:
        q = self._build_query(query)
        if not q:
            return []

        lim = max(1, min(int(limit), 1000))
        params = {
            "query": q,
            "format": "json",
            "pageSize": lim,
        }
        url = f"{self._API_URL}?{urllib.parse.urlencode(params)}"
        payload = self._request_json(url)
        rows = payload.get("resultList", {}).get("result")
        if not isinstance(rows, list):
            return []

        out: list[PaperCandidate] = []
        for record in rows:
            if not isinstance(record, dict):
                continue
            out.append(
                self._to_candidate(
                    record=record,
                    source_key=self.SOURCE_KEY,
                    source_label=self.SOURCE_LABEL,
                    prefer_pubmed_detail=self._prefer_pubmed_detail(),
                )
            )
            if len(out) >= lim:
                break
        return out


class EuropePmcSource(_EuropePmcMixin):
    SOURCE_KEY = "europe_pmc"
    SOURCE_LABEL = "Europe PMC"


class PubMedSource(_EuropePmcMixin):
    SOURCE_KEY = "pubmed"
    SOURCE_LABEL = "PubMed"

    def _build_query(self, query: str) -> str:
        q = str(query or "").strip()
        if not q:
            return ""
        return f"{q} SRC:MED"

    def _prefer_pubmed_detail(self) -> bool:
        return True
