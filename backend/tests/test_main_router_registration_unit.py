from __future__ import annotations

import unittest

from backend.app.core import config as config_module

config_module.settings = config_module.Settings(
    _env_file=None,
    DEBUG=True,
    JWT_SECRET_KEY="unit-test-secret",
)

from backend.app.main import _build_router_registration_specs, create_app


class MainRouterRegistrationUnitTests(unittest.TestCase):
    def test_router_specs_use_direct_router_refs(self):
        specs = _build_router_registration_specs()

        self.assertGreater(len(specs), 0)
        self.assertTrue(all(spec.router is not None or spec.router_factory is not None for spec in specs))
        self.assertTrue(any(spec.router_factory is not None for spec in specs))

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
