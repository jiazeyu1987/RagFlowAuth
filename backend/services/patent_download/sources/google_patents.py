from __future__ import annotations

import json
import time
import urllib.parse
import urllib.error
import urllib.request

from .base import PatentCandidate, PatentSourceError


class GooglePatentsSource:
    SOURCE_KEY = "google_patents"
    SOURCE_LABEL = "Google Patents"

    _QUERY_ENDPOINT = "https://patents.google.com/xhr/query?url="
    _PATENT_IMAGES_HOST = "https://patentimages.storage.googleapis.com/"
    _DETAIL_HOST = "https://patents.google.com/"
    _USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )
    _MAX_RETRIES = 6
    _RETRIABLE_HTTP_STATUS = {429, 500, 502, 503, 504}

    def _retry_after_seconds(self, error: urllib.error.HTTPError) -> float:
        value = ""
        try:
            value = str(error.headers.get("Retry-After", "")).strip()
        except Exception:
            value = ""
        if not value:
            return 0.0
        try:
            return max(0.0, float(value))
        except ValueError:
            return 0.0

    def _calc_backoff_seconds(self, attempt: int, error: Exception) -> float:
        base = min(20.0, 1.4 * (2 ** attempt))
        jitter = 0.15 * (attempt + 1)
        if isinstance(error, urllib.error.HTTPError):
            retry_after = self._retry_after_seconds(error)
            if retry_after > 0:
                return max(base + jitter, retry_after)
        return base + jitter

    def _urlopen_with_retry(self, req: urllib.request.Request, timeout: int):
        last_error: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                return urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in self._RETRIABLE_HTTP_STATUS or attempt >= self._MAX_RETRIES - 1:
                    raise
                time.sleep(self._calc_backoff_seconds(attempt, error))
            except urllib.error.URLError as error:
                last_error = error
                if attempt >= self._MAX_RETRIES - 1:
                    raise
                time.sleep(self._calc_backoff_seconds(attempt, error))
        if last_error is not None:
            raise last_error
        raise RuntimeError("unexpected_network_retry_state")

    def _request_json(self, url: str) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://patents.google.com/",
                "User-Agent": self._USER_AGENT,
            },
        )
        try:
            with self._urlopen_with_retry(req, timeout=45) as resp:
                raw = resp.read()
        except Exception as e:
            raise PatentSourceError(f"google_query_failed: {e}") from e

        try:
            return json.loads(raw.decode("utf-8", errors="ignore"))
        except Exception as e:
            raise PatentSourceError(f"google_query_invalid_json: {e}") from e

    def _build_pdf_url(self, pdf_value: str | None) -> str | None:
        if not pdf_value:
            return None
        text = str(pdf_value).strip()
        if not text:
            return None
        if text.startswith("http://") or text.startswith("https://"):
            return text
        return self._PATENT_IMAGES_HOST + text.lstrip("/")

    def _build_url(self, query: str, *, page: int, num: int, language: str | None = None) -> str:
        params = {
            "q": str(query or "").strip(),
            "num": str(num),
            "page": str(max(0, int(page))),
        }
        if language:
            params["language"] = language
        inner = urllib.parse.urlencode(params)
        url = self._QUERY_ENDPOINT + urllib.parse.quote(inner, safe="")
        return url

    @staticmethod
    def _quote_query(query: str) -> str:
        q = str(query or "").strip()
        if not q:
            return ""
        if len(q) >= 2 and q.startswith('"') and q.endswith('"'):
            return q
        return f'"{q}"'

    def _extract_candidates_from_payload(self, payload: dict, *, limit: int) -> list[PatentCandidate]:
        clusters = payload.get("results", {}).get("cluster", [])
        if not isinstance(clusters, list):
            return []

        rows: list[PatentCandidate] = []
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            result = cluster.get("result")
            if not isinstance(result, list):
                continue
            for item in result:
                if not isinstance(item, dict):
                    continue
                pid = str(item.get("id") or "").strip()
                patent = item.get("patent")
                if not isinstance(patent, dict):
                    continue

                pub_num = str(patent.get("publication_number") or "").strip()
                title = str(patent.get("title") or pub_num or pid or "(untitled patent)").strip()
                detail_url = self._DETAIL_HOST + pid.lstrip("/") if pid else ""

                rows.append(
                    PatentCandidate(
                        source=self.SOURCE_KEY,
                        source_label=self.SOURCE_LABEL,
                        patent_id=pid or pub_num or title,
                        title=title,
                        abstract_text=str(patent.get("snippet") or "").strip(),
                        publication_number=pub_num,
                        publication_date=str(patent.get("publication_date") or "").strip(),
                        inventor=str(patent.get("inventor") or "").strip(),
                        assignee=str(patent.get("assignee") or "").strip(),
                        detail_url=detail_url,
                        pdf_url=self._build_pdf_url(patent.get("pdf")),
                    )
                )
                if len(rows) >= int(limit):
                    return rows

        return rows

    def _search_once(self, *, query: str, limit: int, language: str | None = None) -> list[PatentCandidate]:
        target = max(1, min(int(limit), 1000))
        page_size = min(100, max(20, target))
        rows: list[PatentCandidate] = []
        seen: set[str] = set()
        page = 0
        max_pages = min(30, max(5, (target + page_size - 1) // page_size + 2))

        while len(rows) < target and page < max_pages:
            url = self._build_url(query=query, page=page, num=page_size, language=language)
            payload = self._request_json(url)
            candidates = self._extract_candidates_from_payload(payload, limit=page_size)
            if not candidates:
                break
            for candidate in candidates:
                key = (
                    str(candidate.patent_id or "").strip()
                    or str(candidate.publication_number or "").strip()
                    or str(candidate.title or "").strip()
                )
                if not key or key in seen:
                    continue
                seen.add(key)
                rows.append(candidate)
                if len(rows) >= target:
                    return rows
            page += 1

            results = payload.get("results", {}) if isinstance(payload, dict) else {}
            try:
                total_pages = int(results.get("total_num_pages", 0) or 0)
            except Exception:
                total_pages = 0
            if total_pages and page >= total_pages:
                break

        return rows

    def search(self, *, query: str, limit: int) -> list[PatentCandidate]:
        q = str(query or "").strip()
        if not q:
            return []
        lim = max(1, min(int(limit), 1000))
        quoted_query = self._quote_query(q)

        # 1) Prefer unrestricted language (Chinese keywords often return better coverage).
        # 2) Fallback to ENGLISH index if unrestricted is empty.
        first = self._search_once(query=quoted_query, limit=lim, language=None)
        if first:
            return first
        return self._search_once(query=quoted_query, limit=lim, language="ENGLISH")
