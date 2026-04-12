import unittest

from backend.app.core.config import DEFAULT_JWT_SECRET_KEY, Settings, validate_jwt_secret


class TestJwtSecretFailFastUnit(unittest.TestCase):
    def test_default_secret_non_debug_rejects(self):
        settings = Settings(_env_file=None, DEBUG=False, JWT_SECRET_KEY=DEFAULT_JWT_SECRET_KEY)

        with self.assertRaisesRegex(RuntimeError, "jwt_secret_key_default_or_empty"):
            validate_jwt_secret(settings)

    def test_custom_secret_non_debug_allows(self):
        settings = Settings(_env_file=None, DEBUG=False, JWT_SECRET_KEY="unit-test-secret")

        validate_jwt_secret(settings)

    def test_debug_allows_default(self):
        settings = Settings(_env_file=None, DEBUG=True, JWT_SECRET_KEY=DEFAULT_JWT_SECRET_KEY)

        validate_jwt_secret(settings)
