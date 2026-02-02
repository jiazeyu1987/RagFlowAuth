from __future__ import annotations

import json

from .context import BackupContext


def write_backup_settings_snapshot(ctx: BackupContext) -> None:
    ctx.raise_if_cancelled()
    if not ctx.pack_dir:
        raise RuntimeError("pack_dir not prepared")
    try:
        (ctx.pack_dir / "backup_settings.json").write_text(
            json.dumps(ctx.settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
