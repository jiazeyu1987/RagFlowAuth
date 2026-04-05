from __future__ import annotations

import html
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from backend.app.core.paths import resolve_repo_path


def is_downloaded_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in {"downloaded", "downloaded_cached"}


def is_truthy_flag(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_keywords(keyword_text: str) -> list[str]:
    parts = re.split(r"[,;\n\r\uFF0C\uFF1B]+", str(keyword_text or ""))
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = str(part or "").strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def build_query(keywords: list[str], use_and: bool) -> str:
    if not keywords:
        return ""
    if len(keywords) == 1:
        return keywords[0]
    return " ".join(keywords) if use_and else " OR ".join(keywords)


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def safe_pdf_filename(name: str, fallback: str, *, default_base: str) -> str:
    base = str(name or "").strip() or str(fallback or default_base).strip()
    base = re.sub(r"[\\/:*?\"<>|]+", "_", base).strip(" .")
    if not base:
        base = default_base
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base


def build_content_disposition(filename: str) -> str:
    try:
        filename.encode("ascii")
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        ascii_filename = filename.encode("ascii", "replace").decode("ascii")
        encoded_filename = urllib.parse.quote(filename)
        return f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"


def download_pdf_bytes(url: str, *, user_agent: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_html_text(value: str | None) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_match_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    return text


def translator_script_path() -> Path:
    return resolve_repo_path("scripts/translate_zh_to_en_example.py")


def parse_translator_output(stdout: str) -> str:
    english = ""
    for line in str(stdout or "").splitlines():
        value = str(line or "").strip()
        if value.upper().startswith("EN:"):
            english = value[3:].strip()
    return english


def translate_query_for_uspto(query: str, *, script_path: Path | None = None, timeout: int = 30) -> str:
    script = script_path or translator_script_path()
    if not script.exists():
        raise RuntimeError(f"translator_script_not_found: {script}")

    proc = subprocess.run(
        [sys.executable, str(script), str(query or "")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=timeout,
        check=False,
    )
    if int(proc.returncode or 0) != 0:
        raise RuntimeError(f"translator_failed: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}")

    translated = parse_translator_output(proc.stdout)
    if not translated:
        raise RuntimeError(f"translator_empty_output: {proc.stdout.strip()}")
    return translated
