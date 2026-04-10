import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch


class TestServerBackupPullToolUIUnit(unittest.TestCase):
    def _build_tool(self, backup_root: Path):
        from tool.maintenance import server_backup_pull_tool as tool_module

        patcher = patch.object(tool_module, "DEFAULT_LOCAL_SAVE_DIR", backup_root)
        patcher.start()
        self.addCleanup(patcher.stop)

        root = tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()

        tool = tool_module.ServerBackupPullTool(root)
        tool.save_path_var.set(str(backup_root))
        tool.refresh_local_backups(notify_empty=False)
        root.update_idletasks()
        return tool_module, tool

    def test_refresh_local_backups_populates_local_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir)
            latest = backup_root / "migration_pack_20260130_112315_160"
            older = backup_root / "migration_pack_20260129_101344"
            latest.mkdir()
            older.mkdir()
            (latest / "auth.db").write_text("x", encoding="utf-8")
            (older / "auth.db").write_text("x", encoding="utf-8")

            tool_module, tool = self._build_tool(backup_root)

            self.assertIs(tool.__class__, tool_module.ServerBackupPullTool)
            self.assertTrue(hasattr(tool, "remote_tree"))
            self.assertTrue(hasattr(tool, "local_tree"))
            children = tool.local_tree.get_children()
            self.assertEqual(len(children), 2)
            first_item = tool.local_tree.item(children[0])
            self.assertTrue(first_item["text"].startswith("2026-01-30 11:23:15"))
            self.assertEqual(first_item["values"][0], latest.name)
            self.assertEqual(tool.status_var.get(), f"本地目录共加载 2 个可恢复备份：{backup_root}")

    def test_pull_requires_remote_selection_even_when_local_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir)
            local_backup = backup_root / "migration_pack_20260130_112315_160"
            local_backup.mkdir()
            (local_backup / "auth.db").write_text("x", encoding="utf-8")

            tool_module, tool = self._build_tool(backup_root)
            local_item_id = tool.local_tree.get_children()[0]
            tool.local_tree.selection_set(local_item_id)
            tool._on_local_backup_selected()

            with patch.object(tool_module.messagebox, "showwarning") as showwarning:
                with patch.object(tool, "_start_background") as start_background:
                    tool.pull_selected_backup()

            showwarning.assert_called_once()
            start_background.assert_not_called()

    def test_load_backups_uses_nas_source_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir)
            tool_module, tool = self._build_tool(backup_root)

            result = tool_module.ServerBackupListResult(
                ok=True,
                backups=[
                    tool_module.ServerBackupEntry(
                        name="migration_pack_20260408_101343_362",
                        display_name="2026-04-08 10:13:43 (增量备份)",
                        backup_type="增量备份",
                        created_at="2026-04-08 10:13:43",
                    )
                ],
                raw="",
                message="ok",
            )

            tool.source_var.set(tool_module.REMOTE_SOURCE_NAS)
            tool._on_source_changed()

            with patch.object(tool_module, "list_nas_backup_dirs", return_value=result) as list_nas:
                with patch.object(
                    tool,
                    "_start_background",
                    side_effect=lambda **kwargs: kwargs["on_done"](kwargs["work"]()),
                ):
                    tool.load_backups()

            list_nas.assert_called_once()
            self.assertEqual(tool.remote_frame.cget("text"), "NAS备份列表")
            self.assertEqual(len(tool.remote_tree.get_children()), 1)
            self.assertIn("NAS 共加载 1 个备份", tool.status_var.get())

    def test_restore_uses_selected_local_backup_even_when_remote_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir)
            local_backup = backup_root / "migration_pack_20260130_112315_160"
            local_backup.mkdir()
            (local_backup / "auth.db").write_text("x", encoding="utf-8")

            tool_module, tool = self._build_tool(backup_root)

            remote_entry = tool_module.ServerBackupEntry(
                name="migration_pack_20260408_101343_362",
                display_name="2026-04-08 10:13:43 (增量备份)",
                backup_type="增量备份",
                created_at="2026-04-08 10:13:43",
            )
            tool.remote_backup_rows["remote-1"] = remote_entry
            tool.remote_tree.insert(
                "",
                tk.END,
                iid="remote-1",
                text=remote_entry.created_at,
                values=(remote_entry.backup_type, remote_entry.name),
            )
            tool.remote_tree.selection_set("remote-1")
            tool._on_remote_backup_selected()

            local_item_id = tool.local_tree.get_children()[0]
            tool.local_tree.selection_set(local_item_id)
            tool._on_local_backup_selected()

            captured: dict[str, Path] = {}

            def fake_restore(*, backup_dir):
                captured["backup_dir"] = Path(backup_dir)
                return object()

            with patch.object(tool_module.messagebox, "askyesno", return_value=True):
                with patch.object(tool_module, "restore_downloaded_backup_to_local", side_effect=fake_restore):
                    with patch.object(
                        tool,
                        "_start_background",
                        side_effect=lambda **kwargs: kwargs["work"](),
                    ) as start_background:
                        tool.restore_selected_backup()

            start_background.assert_called_once()
            self.assertEqual(captured["backup_dir"], local_backup)

    def test_pull_selected_nas_backup_uses_nas_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir) / "local"
            backup_root.mkdir()
            tool_module, tool = self._build_tool(backup_root)
            tool.save_path_var.set(str(backup_root))
            tool.source_var.set(tool_module.REMOTE_SOURCE_NAS)
            tool._on_source_changed()

            remote_entry = tool_module.ServerBackupEntry(
                name="migration_pack_20260408_101343_362",
                display_name="2026-04-08 10:13:43 (增量备份)",
                backup_type="增量备份",
                created_at="2026-04-08 10:13:43",
            )
            tool.remote_backup_rows["remote-1"] = remote_entry
            tool.remote_tree.insert(
                "",
                tk.END,
                iid="remote-1",
                text=remote_entry.created_at,
                values=(remote_entry.backup_type, remote_entry.name),
            )
            tool.remote_tree.selection_set("remote-1")
            tool._on_remote_backup_selected()

            captured: dict[str, str] = {}

            def fake_download(*, name, destination_root):
                captured["name"] = name
                captured["destination_root"] = str(destination_root)
                return tool_module.ServerBackupDownloadResult(
                    ok=False,
                    name=name,
                    destination=str(Path(destination_root) / name),
                    raw="boom",
                    message="destination_same_as_source",
                )

            with patch.object(tool_module, "download_nas_backup_dir", side_effect=fake_download):
                with patch.object(
                    tool,
                    "_start_background",
                    side_effect=lambda **kwargs: kwargs["on_done"](kwargs["work"]()),
                ):
                    with patch.object(tool_module.messagebox, "showerror"):
                        tool.pull_selected_backup()

            self.assertEqual(captured["name"], remote_entry.name)
            self.assertEqual(captured["destination_root"], str(backup_root))

    def test_finish_pull_backup_refreshes_local_list_and_selects_downloaded_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_root = Path(tmpdir)
            tool_module, tool = self._build_tool(backup_root)

            downloaded_dir = backup_root / "migration_pack_20260408_101343_362"
            downloaded_dir.mkdir()
            (downloaded_dir / "auth.db").write_text("x", encoding="utf-8")

            result = tool_module.ServerBackupDownloadResult(
                ok=True,
                name=downloaded_dir.name,
                destination=str(downloaded_dir),
                raw="",
                message="downloaded",
            )

            with patch.object(tool_module.messagebox, "showinfo") as showinfo:
                tool._finish_pull_backup(result, tool_module.REMOTE_SOURCE_SERVER)

            showinfo.assert_called_once()
            children = tool.local_tree.get_children()
            self.assertEqual(len(children), 1)
            selected = tool.local_tree.selection()
            self.assertEqual(len(selected), 1)
            selected_item = tool.local_tree.item(selected[0])
            self.assertEqual(selected_item["values"][0], downloaded_dir.name)
            self.assertIn(str(downloaded_dir), tool.status_var.get())
