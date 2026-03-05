import unittest
from unittest.mock import patch

from backend.services.onlyoffice_security import create_file_access_token, parse_file_access_token


class TestOnlyOfficeSecurityUnit(unittest.TestCase):
    @patch("backend.services.onlyoffice_security.settings.ONLYOFFICE_FILE_TOKEN_SECRET", "unit-test-secret")
    @patch("backend.services.onlyoffice_security.settings.JWT_SECRET_KEY", "fallback-secret")
    def test_create_and_parse_token(self):
        token = create_file_access_token({"source": "knowledge", "doc_id": "d1"}, ttl_seconds=120)
        claims = parse_file_access_token(token)
        self.assertEqual(claims.get("source"), "knowledge")
        self.assertEqual(claims.get("doc_id"), "d1")
        self.assertIn("exp", claims)

    @patch("backend.services.onlyoffice_security.settings.ONLYOFFICE_FILE_TOKEN_SECRET", "unit-test-secret")
    @patch("backend.services.onlyoffice_security.settings.JWT_SECRET_KEY", "fallback-secret")
    def test_parse_rejects_expired_token(self):
        with patch("backend.services.onlyoffice_security.time.time", return_value=1000):
            token = create_file_access_token({"source": "knowledge", "doc_id": "d1"}, ttl_seconds=60)
        with patch("backend.services.onlyoffice_security.time.time", return_value=2000):
            with self.assertRaises(ValueError):
                parse_file_access_token(token)


if __name__ == "__main__":
    unittest.main()

