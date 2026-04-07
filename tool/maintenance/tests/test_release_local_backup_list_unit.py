import unittest
from pathlib import Path
from types import SimpleNamespace


class _Var:
    def __init__(self, value=""):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class _Combo:
    def __init__(self):
        self.values = []

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)


class _Label:
    def __init__(self):
        self.text = ""
        self.foreground = ""

    def config(self, **kw):
        if "text" in kw:
            self.text = kw["text"]
        if "foreground" in kw:
            self.foreground = kw["foreground"]


class TestReleaseLocalBackupListUnit(unittest.TestCase):
    def test_refresh_sets_default_to_latest(self):
        # Import the real class method without constructing the full Tk app.
        from tool.maintenance.tool import RagflowAuthTool
        from tool.maintenance.features.local_backup_catalog import BackupCatalogEntry

        # Fake entries (already sorted newest-first by list_local_backups)
        entries = [
            BackupCatalogEntry(path=Path(r"D:\datas\RagflowAuth\migration_pack_20260201_010101"), label="2026-02-01 01:01:01", sort_key=(-3, "a")),
            BackupCatalogEntry(path=Path(r"D:\datas\RagflowAuth\migration_pack_20260131_235959"), label="2026-01-31 23:59:59", sort_key=(-2, "b")),
        ]

        app = SimpleNamespace()
        app.release_local_backup_map = {}
        app.release_local_backup_var = _Var("")
        app.release_local_backup_combo = _Combo()
        app.release_local_backup_note = _Label()

        # Monkeypatch the imported alias on the instance method module namespace.
        import tool.maintenance.tool as tool_mod
        old_fn = tool_mod.feature_list_local_backups
        try:
            tool_mod.feature_list_local_backups = lambda root: entries
            RagflowAuthTool.refresh_release_local_backup_list(app)  # type: ignore[arg-type]
        finally:
            tool_mod.feature_list_local_backups = old_fn

        self.assertEqual(len(app.release_local_backup_combo.values), 2)
        self.assertTrue(app.release_local_backup_var.get())
        self.assertIn(app.release_local_backup_var.get(), app.release_local_backup_map)

