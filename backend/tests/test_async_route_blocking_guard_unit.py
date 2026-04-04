from __future__ import annotations

import ast
from pathlib import Path
import unittest


CRITICAL_ROUTE_FILES = [
    "backend/app/modules/auth/router.py",
    "backend/app/modules/chat/routes_chats.py",
    "backend/app/modules/chat/routes_sessions.py",
    "backend/app/modules/documents/router.py",
    "backend/app/modules/knowledge/routes/admin.py",
    "backend/app/modules/knowledge/routes/files.py",
    "backend/app/modules/knowledge/routes/documents.py",
    "backend/app/modules/knowledge/routes/directory.py",
    "backend/app/modules/knowledge/routes/upload.py",
    "backend/app/modules/operation_approvals/router.py",
    "backend/app/modules/ragflow/routes/documents.py",
    "backend/app/modules/ragflow/routes/datasets.py",
    "backend/app/modules/ragflow/routes/downloads.py",
]


class AsyncRouteBlockingGuardUnitTests(unittest.TestCase):
    def test_async_defs_in_critical_routes_must_use_await(self):
        repo_root = Path(__file__).resolve().parents[2]
        violations: list[str] = []
        for rel_path in CRITICAL_ROUTE_FILES:
            path = repo_root / rel_path
            source = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                has_await = any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node))
                if not has_await:
                    violations.append(f"{rel_path}:{node.lineno}:{node.name}")

        self.assertEqual([], violations, f"Found async route handlers without await: {violations}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
