from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from uuid import uuid4


def make_temp_dir(*, prefix: str = "ragflowauth_test") -> Path:
    """
    Create a writable temp directory without using `tempfile.mkdtemp()`.

    Some Windows environments deny write access to directories created via
    `tempfile.mkdtemp()` / `TemporaryDirectory()`, but still allow writing under
    `tempfile.gettempdir()` when the directory is created explicitly.
    """
    root = Path(tempfile.gettempdir()) / prefix / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def cleanup_dir(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

