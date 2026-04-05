def run_restore_postcheck(app):
    """Run post-restore base_url guard and refresh UI, best-effort."""
    try:
        app._guard_ragflow_base_url(role="test", stage="RESTORE POST")
        app.root.after(0, app.refresh_ragflow_base_urls)
    except Exception as exc:
        app.append_restore_log(f"[WARN] base_url post-check failed: {exc}")
