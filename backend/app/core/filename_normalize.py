from __future__ import annotations

import os
import re


_TRAILING_COPY_PATTERNS = [
    # 123(1) / 123 (1) / 123（1） / 123 （1）
    re.compile(r"(?i)\s*[\(（]\s*\d+\s*[\)）]\s*$"),
    # 123_副本 / 123-副本 / 123 副本 / 123(副本) / 123（副本）
    re.compile(r"\s*[_\-\s]*副本\s*$"),
    re.compile(r"\s*[\(（]\s*副本\s*[\)）]\s*$"),
    # 123_copy / 123-copy / 123 copy
    re.compile(r"(?i)\s*[_\-\s]*copy\s*$"),
]


def normalize_filename_for_conflict(filename: str) -> str:
    """
    Normalize filenames to detect "same file" conflicts like:
    - 123.txt vs 123(1).txt
    - 123.txt vs 123_副本.txt

    Keeps the extension and normalizes only the stem.
    """
    if not isinstance(filename, str):
        return ""

    name = filename.strip()
    if not name:
        return ""

    stem, ext = os.path.splitext(name)
    stem = stem.strip()

    # Iteratively strip common "copy suffixes"
    changed = True
    while changed:
        changed = False
        for pat in _TRAILING_COPY_PATTERNS:
            new = pat.sub("", stem).strip()
            if new != stem:
                stem = new
                changed = True

    # Collapse internal whitespace (helps with "123  (1)" etc.)
    stem = re.sub(r"\s+", " ", stem).strip()
    ext = ext.strip().lower()
    return f"{stem}{ext}"

