from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReleaseHistoryView:
    ok: bool
    text: str
    path: str


def load_release_history(*, path: str = "doc/maintenance/release_history.md", tail_lines: int = 200) -> ReleaseHistoryView:
    """
    Load local release history for display/copy.

    This file is written by the tool itself (see `_record_release_event`).
    """
    p = Path(path)
    if not p.exists():
        return ReleaseHistoryView(
            ok=False,
            path=str(p),
            text=(
                "# 发布记录（尚未生成）\n\n"
                f"- 文件不存在：`{p}`\n"
                "- 说明：当你在“发布”页签执行发布/数据同步/回滚成功后，会自动追加到该文件。\n"
            ),
        )

    content = p.read_text(encoding="utf-8", errors="replace")
    if tail_lines <= 0:
        return ReleaseHistoryView(ok=True, text=content, path=str(p))

    lines = content.splitlines()
    if len(lines) <= tail_lines:
        return ReleaseHistoryView(ok=True, text=content, path=str(p))

    tail = "\n".join(lines[-tail_lines:]) + "\n"
    header = "# 发布记录（尾部截取）\n\n"
    header += f"> 显示最后 {tail_lines} 行；完整内容见：`{p}`\n\n"
    return ReleaseHistoryView(ok=True, text=header + tail, path=str(p))

