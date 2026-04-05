from __future__ import annotations


def request_base_url_refresh(app) -> None:
    try:
        app.root.after(0, app.refresh_ragflow_base_urls)
    except Exception:
        pass


def log_result_lines(*, log_to_file, prefix: str, result_log: str | None, level: str) -> None:
    for line in (result_log or "").splitlines():
        log_to_file(f"{prefix} {line}", level)
