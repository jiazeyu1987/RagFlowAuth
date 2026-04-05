from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from uuid import uuid4


def make_temp_dir(*, prefix: str = "ragflowauth") -> Path:
    """
    Create a writable temporary directory.

    Notes:
    - Some Windows environments allow writing under `tempfile.gettempdir()` but deny writes
      to directories created via `tempfile.mkdtemp()` / `TemporaryDirectory()` (ACL/AV).
    - This helper avoids `mkdtemp()` and creates a unique directory explicitly.
    """
    root = Path(tempfile.gettempdir()) / f"{prefix}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cleanup_dir(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

