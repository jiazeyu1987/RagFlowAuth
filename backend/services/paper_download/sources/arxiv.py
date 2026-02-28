from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .base import PaperCandidate, PaperSourceError


class ArxivSource:
    SOURCE_KEY = "arxiv"
    SOURCE_LABEL = "arXiv"
    _API_URL = "https://export.arxiv.org/api/query"
    _USER_AGENT = "paper-download-arxiv/1.0"

    @staticmethod
    def _quote_query(query: str) -> str:
        q = str(query or "").strip()
        if not q:
            return ""
        if len(q) >= 2 and q.startswith('"') and q.endswith('"'):
            return q
        return f'"{q}"'

    def _build_search_query(self, query: str) -> str:
        quoted = self._quote_query(query)
        return f"all:{quoted}" if quoted else ""

    def search(self, *, query: str, limit: int) -> list[PaperCandidate]:
        q = str(query or "").strip()
        if not q:
            return []
        lim = max(1, min(int(limit), 1000))
        params = {
            "search_query": self._build_search_query(q),
            "start": 0,
            "max_results": lim,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        url = f"{self._API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": self._USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
        except Exception as e:
            raise PaperSourceError(f"arxiv_query_failed: {e}") from e

        try:
            root = ET.fromstring(raw)
        except Exception as e:
            raise PaperSourceError(f"arxiv_query_invalid_xml: {e}") from e

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        rows: list[PaperCandidate] = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").replace("\n", " ").strip()
            abstract_text = (entry.findtext("atom:summary", default="", namespaces=ns) or "").replace("\n", " ").strip()
            detail_url = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
            publication_date = published[:10] if len(published) >= 10 else published
            paper_id = detail_url.rsplit("/", 1)[-1].strip() if detail_url else ""

            authors: list[str] = []
            for author in entry.findall("atom:author", ns):
                name = (author.findtext("atom:name", default="", namespaces=ns) or "").strip()
                if name:
                    authors.append(name)

            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                href = str(link.attrib.get("href") or "").strip()
                link_type = str(link.attrib.get("type") or "").strip().lower()
                link_title = str(link.attrib.get("title") or "").strip().lower()
                if href and ("application/pdf" == link_type or link_title == "pdf"):
                    pdf_url = href
                    break
            if not pdf_url and paper_id:
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

            rows.append(
                PaperCandidate(
                    source=self.SOURCE_KEY,
                    source_label=self.SOURCE_LABEL,
                    patent_id=paper_id or title,
                    title=title or paper_id or "(untitled paper)",
                    abstract_text=abstract_text,
                    publication_number=paper_id,
                    publication_date=publication_date,
                    inventor=", ".join(authors),
                    assignee="",
                    detail_url=detail_url,
                    pdf_url=pdf_url or None,
                )
            )
            if len(rows) >= lim:
                break
        return rows
