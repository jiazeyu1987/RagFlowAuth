from __future__ import annotations

from pathlib import Path, PurePosixPath


CONTROLLED_COMPLIANCE_ROOT = PurePosixPath("docs/compliance")


def controlled_compliance_relpath(*parts: str) -> str:
    return CONTROLLED_COMPLIANCE_ROOT.joinpath(*parts).as_posix()


def controlled_compliance_abs_path(repo_root: str | Path, *parts: str) -> Path:
    return Path(repo_root).resolve() / Path(*CONTROLLED_COMPLIANCE_ROOT.parts) / Path(*parts)
