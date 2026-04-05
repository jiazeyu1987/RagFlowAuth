from __future__ import annotations

import unittest

from backend.app.main import create_app


class MainRouterRegistrationUnitTests(unittest.TestCase):
    def test_create_app_registers_expected_public_routes(self):
        app = create_app()
        paths = {route.path for route in app.routes}

        expected_paths = {
            "/",
            "/health",
            "/api/auth/login",
            "/api/knowledge/documents",
            "/api/package-drawing/by-model",
            "/api/nas/files",
            "/api/permission-groups",
            "/api/paper-download/sessions",
            "/api/patent-download/sessions",
        }

        for path in expected_paths:
            with self.subTest(path=path):
                self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
