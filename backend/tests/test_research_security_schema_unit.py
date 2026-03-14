import os
import sqlite3
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestResearchSecuritySchemaUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_research_security_schema")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_paper_plag_tables_created(self):
        conn = self._conn()
        try:
            tables = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            self.assertIn("paper_versions", tables)
            self.assertIn("paper_plag_reports", tables)
            self.assertIn("paper_plag_hits", tables)

            versions_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(paper_versions)").fetchall()
            }
            self.assertIn("paper_id", versions_cols)
            self.assertIn("version_no", versions_cols)
            self.assertIn("content_hash", versions_cols)

            reports_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(paper_plag_reports)").fetchall()
            }
            self.assertIn("report_id", reports_cols)
            self.assertIn("status", reports_cols)
            self.assertIn("report_file_path", reports_cols)

            hits_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(paper_plag_hits)").fetchall()
            }
            self.assertIn("report_id", hits_cols)
            self.assertIn("start_offset", hits_cols)
            self.assertIn("end_offset", hits_cols)
        finally:
            conn.close()

    def test_egress_decision_audits_table_created(self):
        conn = self._conn()
        try:
            tables = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            }
            self.assertIn("egress_decision_audits", tables)
            self.assertIn("egress_policy_settings", tables)
            self.assertIn("system_feature_flags", tables)

            cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(egress_decision_audits)").fetchall()
            }
            self.assertIn("actor_user_id", cols)
            self.assertIn("policy_mode", cols)
            self.assertIn("decision", cols)
            self.assertIn("hit_rules_json", cols)
            self.assertIn("created_at_ms", cols)

            policy_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(egress_policy_settings)").fetchall()
            }
            self.assertIn("mode", policy_cols)
            self.assertIn("minimal_egress_enabled", policy_cols)
            self.assertIn("domestic_model_allowlist_json", policy_cols)
            self.assertIn("sensitivity_rules_json", policy_cols)
            self.assertIn("updated_at_ms", policy_cols)

            feature_cols = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(system_feature_flags)").fetchall()
            }
            self.assertIn("flag_key", feature_cols)
            self.assertIn("enabled", feature_cols)
            self.assertIn("updated_at_ms", feature_cols)
        finally:
            conn.close()

    def test_egress_policy_defaults_seeded(self):
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT mode, domestic_model_allowlist_json, sensitivity_rules_json
                FROM egress_policy_settings
                WHERE id = 1
                """
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(str(row["mode"]), "intranet")
            self.assertIn("qwen-plus", str(row["domestic_model_allowlist_json"]))
            self.assertIn("high", str(row["sensitivity_rules_json"]))
        finally:
            conn.close()

    def test_system_feature_flag_defaults_seeded(self):
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT flag_key, enabled
                FROM system_feature_flags
                WHERE flag_key IN ('paper_plag_enabled', 'egress_policy_enabled', 'research_ui_layout_enabled')
                ORDER BY flag_key
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(bool(row["enabled"]) for row in rows))
        finally:
            conn.close()

    def test_research_security_indexes_created(self):
        conn = self._conn()
        try:
            index_names = {
                str(row["name"])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
            }
        finally:
            conn.close()

        expected = {
            "idx_paper_versions_paper_created",
            "idx_paper_versions_author_updated",
            "idx_paper_plag_reports_paper_created",
            "idx_paper_plag_reports_status_created",
            "idx_paper_plag_reports_task_id",
            "idx_paper_plag_hits_report_similarity",
            "idx_paper_plag_hits_report_offset",
            "idx_egress_decision_audits_created",
            "idx_egress_decision_audits_actor_created",
            "idx_egress_decision_audits_decision_created",
            "idx_egress_decision_audits_target_host",
            "idx_system_feature_flags_enabled",
        }
        for name in expected:
            self.assertIn(name, index_names)

    def test_ensure_schema_idempotent_for_research_security_tables(self):
        ensure_schema(self.db_path)

        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name = 'paper_plag_reports'"
            ).fetchone()
            self.assertEqual(int(row["c"] or 0), 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
