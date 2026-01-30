from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path

from backend.services.office_to_pdf import ensure_soffice_available
import subprocess


def _run_soffice_convert_to_html(input_path: Path, outdir: Path) -> Path:
    exe = ensure_soffice_available()
    cmd = [
        exe,
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to",
        "html",
        "--outdir",
        str(outdir),
        str(input_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"soffice convert failed: {proc.stderr.strip() or proc.stdout.strip()}")

    html_candidates = list(outdir.glob("*.html")) + list(outdir.glob("*.htm"))
    if not html_candidates:
        raise RuntimeError("soffice did not produce an HTML output")
    return html_candidates[0]


_SRC_RE = re.compile(r"""(?P<prefix>\bsrc=)(?P<q>["'])(?P<val>[^"']+)(?P=q)""", re.IGNORECASE)
_HREF_RE = re.compile(r"""(?P<prefix>\bhref=)(?P<q>["'])(?P<val>[^"']+)(?P=q)""", re.IGNORECASE)


def _mime_for_ext(ext: str) -> str:
    e = (ext or "").lower().lstrip(".")
    if e in ("png",):
        return "image/png"
    if e in ("jpg", "jpeg"):
        return "image/jpeg"
    if e in ("gif",):
        return "image/gif"
    if e in ("svg",):
        return "image/svg+xml"
    if e in ("bmp",):
        return "image/bmp"
    if e in ("webp",):
        return "image/webp"
    if e in ("css",):
        return "text/css; charset=utf-8"
    return "application/octet-stream"


def _inline_rel_resources(html: str, base_dir: Path) -> str:
    """
    Inline relative src/href resources (images/css) into a single HTML document.
    """

    def repl_src(m: re.Match) -> str:
        val = m.group("val")
        if val.startswith(("http://", "https://", "data:", "blob:")):
            return m.group(0)
        p = (base_dir / val).resolve()
        if not p.exists() or not p.is_file():
            return m.group(0)
        mime = _mime_for_ext(p.suffix)
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'{m.group("prefix")}{m.group("q")}data:{mime};base64,{data}{m.group("q")}'

    def repl_href(m: re.Match) -> str:
        val = m.group("val")
        if val.startswith(("http://", "https://", "data:", "blob:")):
            return m.group(0)
        p = (base_dir / val).resolve()
        if not p.exists() or not p.is_file():
            return m.group(0)
        if p.suffix.lower() == ".css":
            css = p.read_text(encoding="utf-8", errors="ignore")
            # Inline CSS as <style> by replacing href with data URL (simpler & works with existing tag).
            data = base64.b64encode(css.encode("utf-8")).decode("ascii")
            return f'{m.group("prefix")}{m.group("q")}data:text/css;base64,{data}{m.group("q")}'
        # Other hrefs: inline as data
        mime = _mime_for_ext(p.suffix)
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'{m.group("prefix")}{m.group("q")}data:{mime};base64,{data}{m.group("q")}'

    html = _SRC_RE.sub(repl_src, html)
    html = _HREF_RE.sub(repl_href, html)
    return html


def _ensure_html_utf8(html_bytes: bytes) -> str:
    # LibreOffice may emit various encodings; decode best-effort and normalize to utf-8 string.
    for enc in ("utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return html_bytes.decode(enc)
        except Exception:
            continue
    return html_bytes.decode("utf-8", errors="ignore")


def convert_office_path_to_html_bytes(path: str | Path) -> bytes:
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(str(src))

    suffix = src.suffix.lower() or ""
    with tempfile.TemporaryDirectory(prefix="office2html_") as tmpdir:
        outdir = Path(tmpdir)
        tmp_src = outdir / f"input{suffix}"
        tmp_src.write_bytes(src.read_bytes())
        html_path = _run_soffice_convert_to_html(tmp_src, outdir)
        html = _ensure_html_utf8(html_path.read_bytes())
        html = _inline_rel_resources(html, html_path.parent)
        return html.encode("utf-8")


def convert_office_bytes_to_html_bytes(content: bytes, *, filename: str = "input") -> bytes:
    suffix = Path(filename).suffix.lower() or ""
    with tempfile.TemporaryDirectory(prefix="office2html_") as tmpdir:
        outdir = Path(tmpdir)
        tmp_src = outdir / f"input{suffix}"
        tmp_src.write_bytes(content)
        html_path = _run_soffice_convert_to_html(tmp_src, outdir)
        html = _ensure_html_utf8(html_path.read_bytes())
        html = _inline_rel_resources(html, html_path.parent)
        return html.encode("utf-8")

