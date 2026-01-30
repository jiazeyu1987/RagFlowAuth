from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def ensure_soffice_available() -> str:
    exe = _find_soffice()
    if not exe:
        raise RuntimeError("soffice not found (LibreOffice is required for office -> pdf preview)")
    return exe


def _run_soffice_convert(input_path: Path, outdir: Path) -> Path:
    exe = ensure_soffice_available()
    cmd = [
        exe,
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to",
        "pdf",
        "--outdir",
        str(outdir),
        str(input_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"soffice convert failed: {proc.stderr.strip() or proc.stdout.strip()}")

    pdf_candidates = list(outdir.glob("*.pdf"))
    if not pdf_candidates:
        raise RuntimeError("soffice did not produce a PDF output")
    return pdf_candidates[0]


def convert_office_path_to_pdf_bytes(path: str | Path) -> bytes:
    """
    Convert an Office file on disk to PDF bytes using LibreOffice (soffice) headless mode.
    Supports .doc/.docx/.xls/.xlsx/.ppt/.pptx etc (depending on installed LO components).
    """
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(str(src))

    suffix = src.suffix.lower() or ""
    with tempfile.TemporaryDirectory(prefix="office2pdf_") as tmpdir:
        outdir = Path(tmpdir)
        tmp_src = outdir / f"input{suffix}"
        tmp_src.write_bytes(src.read_bytes())
        pdf_path = _run_soffice_convert(tmp_src, outdir)
        return pdf_path.read_bytes()


def convert_office_bytes_to_pdf_bytes(content: bytes, *, filename: str = "input") -> bytes:
    """
    Convert Office bytes to PDF bytes using LibreOffice (soffice) headless mode.
    """
    suffix = Path(filename).suffix.lower() or ""
    with tempfile.TemporaryDirectory(prefix="office2pdf_") as tmpdir:
        outdir = Path(tmpdir)
        tmp_src = outdir / f"input{suffix}"
        tmp_src.write_bytes(content)
        pdf_path = _run_soffice_convert(tmp_src, outdir)
        return pdf_path.read_bytes()

