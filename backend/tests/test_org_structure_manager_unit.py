import os
import sqlite3
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from backend.database.schema.ensure import ensure_schema
from backend.services.org_directory import manager as org_manager_module
from backend.services.org_directory import OrgDirectoryStore, OrgStructureManager
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestOrgStructureManagerUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_org_structure_manager")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = OrgDirectoryStore(db_path=self.db_path)
        self.manager = OrgStructureManager(store=self.store)

    def tearDown(self):
        cleanup_dir(self._tmp)

    @staticmethod
    def _flatten_tree(nodes):
        flattened = []
        stack = list(nodes)
        while stack:
            node = stack.pop(0)
            flattened.append(node)
            stack[0:0] = list(node.get("children") or [])
        return flattened

    def test_rebuild_from_excel_creates_expected_tree_and_stable_ids(self):
        summary = self.manager.rebuild_from_excel(actor_user_id="admin-1")
        companies = self.manager.list_companies()
        departments = self.manager.list_departments_flat()
        employees = self.manager.list_employees()
        tree_nodes = self._flatten_tree(self.manager.get_tree())
        person_nodes = [item for item in tree_nodes if item.get("node_type") == "person"]

        self.assertEqual(summary.company_count, 21)
        self.assertEqual(summary.department_count, 302)
        self.assertEqual(summary.employee_count, 2027)
        self.assertEqual(len(companies), 21)
        self.assertEqual(len(departments), 302)
        self.assertEqual(len(employees), 2027)
        self.assertEqual(len(person_nodes), 2027)
        self.assertEqual(max(item.level_no for item in departments), 7)

        duplicate_names = [name for name, count in Counter(item.name for item in departments).items() if count > 1]
        self.assertTrue(duplicate_names)
        self.assertTrue(any((item.path_name or "").count(" / ") >= 1 for item in departments))
        self.assertTrue(any(item.department_id is None for item in employees))
        self.assertTrue(any(item.department_id is not None for item in employees))
        self.assertTrue(all(item.get("employee_user_id") for item in person_nodes))
        self.assertTrue(any(item.department_manager_name for item in employees))
        self.assertTrue(any(item.is_department_manager for item in employees))
        self.assertTrue(any(item.get("is_department_manager") for item in person_nodes))

        company_ids_before = {item.source_key: item.company_id for item in companies}
        department_ids_before = {item.source_key: item.department_id for item in departments}
        employee_ids_before = {item.source_key: item.employee_id for item in employees}

        second_summary = self.manager.rebuild_from_excel(actor_user_id="admin-1")
        self.assertEqual(second_summary.company_count, 21)
        self.assertEqual(second_summary.department_count, 302)
        self.assertEqual(second_summary.employee_count, 2027)

        company_ids_after = {item.source_key: item.company_id for item in self.manager.list_companies()}
        department_ids_after = {item.source_key: item.department_id for item in self.manager.list_departments_flat()}
        employee_ids_after = {item.source_key: item.employee_id for item in self.manager.list_employees()}
        self.assertEqual(company_ids_before, company_ids_after)
        self.assertEqual(department_ids_before, department_ids_after)
        self.assertEqual(employee_ids_before, employee_ids_after)

    def test_rebuild_clears_stale_user_refs_and_populates_source_department_ids(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO companies (company_id, name, source_key, created_at_ms, updated_at_ms)
                VALUES (9001, 'Legacy Company', 'legacy_company:9001', 1, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO departments (
                    department_id,
                    name,
                    company_id,
                    parent_department_id,
                    source_key,
                    source_department_id,
                    level_no,
                    path_name,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (9002, "Legacy Department", 9001, None, "legacy_department:9002", None, 1, "Legacy Department", 0, 1, 1),
            )
            conn.execute(
                """
                INSERT INTO org_employees (
                    employee_id,
                    employee_user_id,
                    name,
                    email,
                    employee_no,
                    department_manager_name,
                    is_department_manager,
                    company_id,
                    department_id,
                    source_key,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (9003, "legacy-user-1", "Legacy Employee", None, None, None, 0, 9001, 9002, "legacy-user-1", 0, 1, 1),
            )
            conn.execute(
                """
                INSERT INTO users (
                    user_id, username, password_hash, role, group_id, company_id, department_id, status, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("legacy-user-1", "legacy-user-1", "hashed", "viewer", None, 9001, 9002, "active", 1),
            )
            conn.commit()
        finally:
            conn.close()

        summary = self.manager.rebuild_from_excel(actor_user_id="admin-1")
        self.assertEqual(summary.users_company_cleared, 1)
        self.assertEqual(summary.users_department_cleared, 1)
        self.assertEqual(summary.employees_deleted, 1)
        self.assertIsNone(self.store.get_company(9001))
        self.assertIsNone(self.store.get_department(9002))
        self.assertIsNone(self.store.get_employee(9003))

        conn = sqlite3.connect(self.db_path)
        try:
            user_row = conn.execute(
                "SELECT company_id, department_id FROM users WHERE user_id = ?",
                ("legacy-user-1",),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(user_row, (None, None))

        departments = self.manager.list_departments_flat()
        populated_source_department_ids = [item.source_department_id for item in departments if item.source_department_id]
        self.assertGreater(len(populated_source_department_ids), 0)
        self.assertEqual(len(populated_source_department_ids), len(set(populated_source_department_ids)))

    def test_parse_excel_rejects_duplicate_employee_user_id(self):
        headers = [
            org_manager_module.HEADER_EMPLOYEE_USER_ID,
            org_manager_module.HEADER_EMPLOYEE_NAME,
            org_manager_module.HEADER_EMPLOYEE_EMAIL,
            org_manager_module.HEADER_EMPLOYEE_NO,
            org_manager_module.HEADER_DEPARTMENT_MANAGER,
            org_manager_module.HEADER_COMPANY,
            *org_manager_module.DEPARTMENT_LEVEL_HEADERS,
            org_manager_module.HEADER_SOURCE_DEPARTMENT_ID,
        ]
        rows = [
            headers,
            ["u-1", "张三", "", "", "张三", "公司A", "部门A", "", "", "", "", "", "1001"],
            ["u-1", "李四", "", "", "李四", "公司A", "部门B", "", "", "", "", "", "1002"],
        ]

        self.manager._excel_path = Path(self.db_path)
        with patch.object(OrgStructureManager, "_load_excel_rows", return_value=rows):
            with self.assertRaisesRegex(RuntimeError, "org_structure_excel_employee_user_id_conflict:u-1"):
                self.manager._parse_excel()

    def test_parse_excel_supports_xlsx_upload_path(self):
        workbook_path = Path(self._tmp) / "org-structure-upload.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                org_manager_module.HEADER_EMPLOYEE_USER_ID,
                org_manager_module.HEADER_EMPLOYEE_NAME,
                org_manager_module.HEADER_EMPLOYEE_EMAIL,
                org_manager_module.HEADER_EMPLOYEE_NO,
                org_manager_module.HEADER_DEPARTMENT_MANAGER,
                org_manager_module.HEADER_COMPANY,
                *org_manager_module.DEPARTMENT_LEVEL_HEADERS,
                org_manager_module.HEADER_SOURCE_DEPARTMENT_ID,
            ]
        )
        sheet.append(["u-100", "王五", "wangwu@example.com", "E100", "王五", "公司A", "部门A", "", "", "", "", "", "D100"])
        workbook.save(workbook_path)
        workbook.close()

        companies, departments, employees = self.manager._parse_excel(excel_path=workbook_path)

        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].source_key, "公司A")
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].source_key, "公司A/部门A")
        self.assertEqual(departments[0].source_department_id, "D100")
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0].employee_user_id, "u-100")
        self.assertTrue(employees[0].is_department_manager)


if __name__ == "__main__":
    unittest.main()
