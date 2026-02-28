from __future__ import annotations

from .base import PatentCandidate
from .google_patents import GooglePatentsSource


class UsptoSource:
    """
    USPTO-oriented source backed by live patent PDF downloads.

    Notes:
    - This implementation uses Google Patents' US corpus query and filters by
      US publication numbers to keep "USPTO" semantics while preserving stable,
      real downloadable PDF links in current deployment environments.
    """

    SOURCE_KEY = "uspto"
    SOURCE_LABEL = "USPTO"

    def __init__(self, google_source: GooglePatentsSource):
        self._google = google_source

    def search(self, *, query: str, limit: int) -> list[PatentCandidate]:
        # Use broader request to compensate for post-filter shrink.
        expanded_limit = max(int(limit) * 3, int(limit))
        raw = self._google.search(query=f"{query} country:US", limit=expanded_limit)

        rows: list[PatentCandidate] = []
        seen: set[str] = set()
        for item in raw:
            pub = str(item.publication_number or "").upper()
            pid = str(item.patent_id or "").upper()
            is_us = pub.startswith("US") or "/US" in pid or pid.startswith("PATENT/US")
            if not is_us:
                continue
            key = (item.patent_id or item.publication_number or item.title).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(
                PatentCandidate(
                    source=self.SOURCE_KEY,
                    source_label=self.SOURCE_LABEL,
                    patent_id=item.patent_id,
                    title=item.title,
                    abstract_text=item.abstract_text,
                    publication_number=item.publication_number,
                    publication_date=item.publication_date,
                    inventor=item.inventor,
                    assignee=item.assignee,
                    detail_url=item.detail_url,
                    pdf_url=item.pdf_url,
                )
            )
            if len(rows) >= int(limit):
                break
        return rows
