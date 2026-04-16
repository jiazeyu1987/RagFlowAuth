import json
import os
import unittest

from backend.services.document_control import (
    DocumentControlMatrixResolver,
    DocumentControlMatrixResolverError,
)
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


KEY_FILE = "\u6587\u4ef6\u5c0f\u7c7b"
KEY_COMPILER = "\u7f16\u5236"
KEY_SIGNOFF = "\u5ba1\u6838\u4f1a\u7b7e"
KEY_APPROVER = "\u6279\u51c6"

POS_DIRECT_MANAGER = "\u7f16\u5236\u4eba\u76f4\u63a5\u4e3b\u7ba1"
POS_DOC_ADMIN = "\u6587\u6863\u7ba1\u7406\u5458"
POS_REG = "\u6ce8\u518c"
POS_TEST_CENTER = "\u68c0\u6d4b\u4e2d\u5fc3"

FILE_PRODUCT_TECH_REQ = "\u4ea7\u54c1\u6280\u672f\u8981\u6c42"
FILE_PROCESS_FLOW = "\u5de5\u827a\u6d41\u7a0b\u56fe"
FILE_PROJECT_PLAN = "\u9879\u76ee\u7b56\u5212\u4e66"
FILE_INSPECTION_MAINT = "\u68c0\u9a8c\u7528\u5de5\u88c5\u6a21\u5177\u7ef4\u62a4\u4fdd\u517b\u89c4\u8303"

ROLE_PROJECT_OWNER = "\u9879\u76ee\u8d1f\u8d23\u4eba"
ROLE_DESIGNEE = "\u6307\u5b9a\u4eba\u5458"
ROLE_PROJECT_OWNER_OR_DESIGNEE = "\u9879\u76ee\u8d1f\u8d23\u4eba\u6216\u6307\u5b9a\u4eba\u5458"
ROLE_TECH = "\u6280\u672f\u4eba\u5458"
ROLE_EQUIPMENT = "\u8bbe\u5907\u4eba\u5458"
ROLE_QA = "QA"
ROLE_QC = "QC"
ROLE_QMS = "QMS"
ROLE_RD_HEAD = "\u7814\u53d1\u90e8\u95e8\u8d1f\u8d23\u4eba"
ROLE_GENERAL_MANAGER = "\u603b\u7ecf\u7406"
ROLE_APPROVER_DEPT = "\u7f16\u5236\u90e8\u95e8\u8d1f\u8d23\u4eba\u6216\u6388\u6743\u4ee3\u8868"
ROLE_RD_HEAD_OR_GM = "\u7814\u53d1\u90e8\u95e8\u8d1f\u8d23\u4eba\u6216\u603b\u7ecf\u7406"

REMARK_USAGE_SCOPE = "\u6839\u636e\u4f7f\u7528\u533a\u57df"


def _write_matrix_json(path: str, items: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(items, handle, ensure_ascii=False, indent=2)


def _write_matrix_html(path: str, rows: list[dict]) -> None:
    objects = []
    for row in rows:
        objects.append(
            "{\n"
            f'  file: "{row["file"]}",\n'
            f'  compiler: "{row["compiler"]}",\n'
            f'  approver: "{row["approver"]}",\n'
            f'  remark: "{row.get("remark", "")}"\n'
            "}"
        )
    payload = "<script>\nconst DATA = { DMR: [\n" + ",\n".join(objects) + "\n] };\n</script>\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)


class TestDocumentControlMatrixResolverUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_matrix_resolver")
        self.matrix_path = os.path.join(str(self._tmp), "matrix.json")
        self.matrix_html_path = os.path.join(str(self._tmp), "matrix.html")
        _write_matrix_json(
            self.matrix_path,
            [
                {
                    KEY_FILE: FILE_PRODUCT_TECH_REQ,
                    KEY_COMPILER: ROLE_PROJECT_OWNER,
                    KEY_SIGNOFF: {
                        POS_DIRECT_MANAGER: "\u25cf",
                        ROLE_QA: "\u25cf",
                        ROLE_QC: "",
                        ROLE_QMS: "\u25cf",
                        POS_REG: "\u25cf",
                        POS_DOC_ADMIN: "\u25cf",
                    },
                    KEY_APPROVER: ROLE_APPROVER_DEPT,
                },
                {
                    KEY_FILE: FILE_PROCESS_FLOW,
                    KEY_COMPILER: ROLE_TECH,
                    KEY_SIGNOFF: {
                        POS_DIRECT_MANAGER: "\u25cf",
                        ROLE_QA: "",
                        ROLE_QC: "\u25cb",
                        ROLE_QMS: "\u25cf",
                        POS_REG: "",
                        POS_DOC_ADMIN: "\u25cf",
                    },
                    KEY_APPROVER: ROLE_GENERAL_MANAGER,
                },
                {
                    KEY_FILE: FILE_PROJECT_PLAN,
                    KEY_COMPILER: ROLE_PROJECT_OWNER_OR_DESIGNEE,
                    KEY_SIGNOFF: {
                        ROLE_QA: "\u25cf",
                        POS_DOC_ADMIN: "\u25cf",
                    },
                    KEY_APPROVER: ROLE_RD_HEAD_OR_GM,
                },
                {
                    KEY_FILE: FILE_INSPECTION_MAINT,
                    KEY_COMPILER: ROLE_EQUIPMENT,
                    KEY_SIGNOFF: {
                        ROLE_QC: "\u25cf",
                        ROLE_QMS: "\u25cf",
                        POS_TEST_CENTER: "\u25cf",
                    },
                    KEY_APPROVER: ROLE_APPROVER_DEPT,
                },
            ],
        )
        _write_matrix_html(
            self.matrix_html_path,
            [
                {"file": FILE_PRODUCT_TECH_REQ, "compiler": ROLE_PROJECT_OWNER, "approver": ROLE_APPROVER_DEPT, "remark": ""},
                {"file": FILE_PROCESS_FLOW, "compiler": ROLE_TECH, "approver": ROLE_GENERAL_MANAGER, "remark": ""},
                {"file": FILE_PROJECT_PLAN, "compiler": ROLE_PROJECT_OWNER_OR_DESIGNEE, "approver": ROLE_RD_HEAD_OR_GM, "remark": ""},
                {"file": FILE_INSPECTION_MAINT, "compiler": ROLE_EQUIPMENT, "approver": ROLE_APPROVER_DEPT, "remark": REMARK_USAGE_SCOPE},
            ],
        )
        self.resolver = DocumentControlMatrixResolver(
            matrix_json_path=self.matrix_path,
            matrix_html_path=self.matrix_html_path,
        )
        self.position_assignments = {
            ROLE_PROJECT_OWNER: [
                {"user_id": "applicant-1", "username": "applicant1", "full_name": "Applicant One"},
            ],
            ROLE_DESIGNEE: [
                {"user_id": "designee-1", "username": "designee1", "full_name": "Designee One"},
            ],
            ROLE_TECH: [
                {"user_id": "tech-1", "username": "tech1", "full_name": "Tech One"},
            ],
            ROLE_EQUIPMENT: [
                {"user_id": "equip-1", "username": "equip1", "full_name": "Equipment One"},
            ],
            ROLE_QA: [
                {"user_id": "qa-1", "username": "qa1", "full_name": "QA One"},
            ],
            ROLE_QC: [
                {"user_id": "qc-1", "username": "qc1", "full_name": "QC One"},
            ],
            ROLE_QMS: [
                {"user_id": "qms-1", "username": "qms1", "full_name": "QMS One"},
            ],
            POS_TEST_CENTER: [
                {"user_id": "test-1", "username": "test1", "full_name": "Test Center One"},
            ],
            POS_REG: [
                {"user_id": "reg-1", "username": "reg1", "full_name": "Reg One"},
            ],
            POS_DOC_ADMIN: [
                {"user_id": "doc-1", "username": "doc1", "full_name": "Doc One"},
            ],
            ROLE_APPROVER_DEPT: [
                {"user_id": "approver-1", "username": "approver1", "full_name": "Approver One"},
            ],
            ROLE_RD_HEAD: [
                {"user_id": "rd-head-1", "username": "rdhead1", "full_name": "RD Head One"},
            ],
            ROLE_GENERAL_MANAGER: [
                {"user_id": "gm-1", "username": "gm1", "full_name": "GM One"},
            ],
        }

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_different_file_subtypes_generate_different_chains(self):
        product = self.resolver.resolve(
            file_subtype=FILE_PRODUCT_TECH_REQ,
            applicant_user_id="applicant-1",
            applicant_manager_user_id="manager-1",
            document_type="sop",
            registration_ref="REG-001",
            position_assignments=self.position_assignments,
        )
        process = self.resolver.resolve(
            file_subtype=FILE_PROCESS_FLOW,
            applicant_user_id="tech-1",
            applicant_manager_user_id="manager-2",
            document_type="sop",
            registration_ref=None,
            position_assignments=self.position_assignments,
        )

        self.assertEqual(
            [item.position_name for item in product.signoff_steps],
            [POS_DIRECT_MANAGER, ROLE_QA, ROLE_QMS, POS_REG, POS_DOC_ADMIN],
        )
        self.assertEqual(
            [item.position_name for item in process.signoff_steps],
            [POS_DIRECT_MANAGER, ROLE_QMS, POS_DOC_ADMIN],
        )
        self.assertEqual([item.position_name for item in product.approval_steps], [ROLE_APPROVER_DEPT])
        self.assertEqual([item.position_name for item in process.approval_steps], [ROLE_GENERAL_MANAGER])

    def test_registration_position_requires_registration_ref(self):
        result = self.resolver.resolve(
            file_subtype=FILE_PRODUCT_TECH_REQ,
            applicant_user_id="applicant-1",
            applicant_manager_user_id="manager-1",
            document_type="sop",
            registration_ref=None,
            position_assignments=self.position_assignments,
        )

        self.assertEqual(
            [item.position_name for item in result.signoff_steps],
            [POS_DIRECT_MANAGER, ROLE_QA, ROLE_QMS, POS_DOC_ADMIN],
        )
        registration_snapshot = next(
            item for item in result.snapshot["signoff_positions"] if item["position_name"] == POS_REG
        )
        self.assertFalse(registration_snapshot["included"])
        self.assertEqual(registration_snapshot["skip_reason"], "registration_ref_missing")

    def test_direct_manager_missing_fails_fast(self):
        with self.assertRaises(DocumentControlMatrixResolverError) as ctx:
            self.resolver.resolve(
                file_subtype=FILE_PRODUCT_TECH_REQ,
                applicant_user_id="applicant-1",
                applicant_manager_user_id=None,
                document_type="sop",
                registration_ref="REG-001",
                position_assignments=self.position_assignments,
            )
        self.assertEqual(ctx.exception.code, "document_control_matrix_direct_manager_missing")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_unassigned_position_fails_fast(self):
        assignments = dict(self.position_assignments)
        assignments[ROLE_QMS] = []

        with self.assertRaises(DocumentControlMatrixResolverError) as ctx:
            self.resolver.resolve(
                file_subtype=FILE_PRODUCT_TECH_REQ,
                applicant_user_id="applicant-1",
                applicant_manager_user_id="manager-1",
                document_type="sop",
                registration_ref="REG-001",
                position_assignments=assignments,
            )
        self.assertEqual(ctx.exception.code, "document_control_matrix_position_unassigned:QMS")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_optional_circle_mark_is_not_added_to_steps(self):
        result = self.resolver.resolve(
            file_subtype=FILE_PROCESS_FLOW,
            applicant_user_id="tech-1",
            applicant_manager_user_id="manager-2",
            document_type="sop",
            registration_ref=None,
            position_assignments=self.position_assignments,
        )

        self.assertNotIn(ROLE_QC, [item.position_name for item in result.signoff_steps])
        qc_snapshot = next(
            item for item in result.snapshot["signoff_positions"] if item["position_name"] == ROLE_QC
        )
        self.assertFalse(qc_snapshot["included"])
        self.assertEqual(qc_snapshot["skip_reason"], "optional_mark")

    def test_combined_compiler_and_approver_positions_support_or_matching(self):
        result = self.resolver.resolve(
            file_subtype=FILE_PROJECT_PLAN,
            applicant_user_id="designee-1",
            applicant_manager_user_id="manager-3",
            document_type="dhf",
            registration_ref=None,
            position_assignments=self.position_assignments,
        )

        self.assertTrue(result.compiler_check.matched)
        self.assertEqual(result.compiler_check.position_name, ROLE_PROJECT_OWNER_OR_DESIGNEE)
        self.assertEqual([item.user_id for item in result.approval_steps[0].approvers], ["rd-head-1", "gm-1"])
        self.assertEqual(result.snapshot["remark"], None)

    def test_usage_scope_remark_requires_usage_scope_metadata(self):
        with self.assertRaises(DocumentControlMatrixResolverError) as ctx:
            self.resolver.resolve(
                file_subtype=FILE_INSPECTION_MAINT,
                applicant_user_id="equip-1",
                applicant_manager_user_id="manager-4",
                document_type="dmr",
                registration_ref=None,
                position_assignments=self.position_assignments,
            )
        self.assertEqual(ctx.exception.code, "document_control_matrix_usage_scope_required")
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
