from ._shared import _tool_mod


def extract_version_from_release_log(text: str | None) -> str | None:
    tool_mod = _tool_mod()
    re = tool_mod.re

    if not text:
        return None
    match = re.search(r"\bVERSION=([0-9_]+)\b", text)
    if match:
        return match.group(1)
    return None


def record_release_event(app, *, event: str, server_ip: str, version: str, details: str) -> None:
    tool_mod = _tool_mod()
    path_cls = tool_mod.Path
    datetime = tool_mod.datetime
    log_to_file = tool_mod.log_to_file
    _ = app

    """
    Append a local release record for audit/rollback purposes.

    File is inside the repo so it can be committed if needed.
    """
    history_path = path_cls("doc/maintenance/release_history.md")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    version = (version or "").strip() or "(unknown)"
    details = (details or "").strip()

    header = "# 发布记录（自动追加）\n\n> 说明：由 `tool/maintenance/tool.py` 自动写入，用于追溯发布/回滚历史。\n\n"
    line = f"- {ts} | {event} | server={server_ip} | version={version}\n"
    if details:
        rendered = details.replace("\r\n", "\n").replace("\r", "\n")
        line += "  - " + rendered.replace("\n", "\n  - ") + "\n"

    try:
        if not history_path.exists():
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history_path.write_text(header, encoding="utf-8")
        with history_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        log_to_file(f"[ReleaseRecord] write failed: {e}", "ERROR")
