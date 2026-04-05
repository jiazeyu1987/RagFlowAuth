from __future__ import annotations

import unittest

from backend.app.main import create_app


class MainRouterRegistrationUnitTests(unittest.TestCase):
    def test_create_app_registers_expected_public_routes(self):
        app = create_app()
        paths = {route.path for route in app.routes}

        self.assertIn("/api/auth/login", paths)
        self.assertIn("/api/knowledge/documents", paths)
        self.assertIn("/api/package-drawing/by-model", paths)
        self.assertIn("/api/nas/files", paths)
        self.assertIn("/health", paths)


if __name__ == "__main__":
    unittest.main()
