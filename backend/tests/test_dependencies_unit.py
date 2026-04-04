import tempfile
import unittest
from pathlib import Path

from backend.app.dependencies import create_dependencies


class TestDependenciesUnit(unittest.TestCase):
    def test_operation_approval_reuses_shared_signature_service_when_control_db_is_separate(self):
        with tempfile.TemporaryDirectory(prefix="ragflowauth_deps_") as temp_dir:
            root = Path(temp_dir)
            main_db = root / "main_auth.db"
            approval_db = root / "approval_auth.db"

            deps = create_dependencies(
                db_path=str(main_db),
                operation_approval_control_db_path=str(approval_db),
            )

            self.assertIsNotNone(deps.electronic_signature_service)
            self.assertIsNotNone(deps.operation_approval_service)
            self.assertIs(
                deps.operation_approval_service._signature_service,
                deps.electronic_signature_service,
            )


if __name__ == "__main__":
    unittest.main()
