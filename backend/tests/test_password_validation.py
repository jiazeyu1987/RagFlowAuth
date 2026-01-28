"""
Unit tests for password validation logic.

Tests password requirements:
- Minimum length: 6 characters
- Must contain letters and numbers
- Common passwords are rejected
"""
import unittest
from backend.services.users import validate_password_requirements


class TestPasswordValidation(unittest.TestCase):
    """Test password validation logic"""

    def test_accepts_valid_password(self):
        """Valid password should pass validation"""
        valid_passwords = [
            "xyz123",      # letters + numbers (not common)
            "Test123",     # mixed case
            "myp@ssw0rd",  # with special char
        ]
        for password in valid_passwords:
            result = validate_password_requirements(password)
            self.assertTrue(result, f"Password '{password}' should be valid")

    def test_rejects_too_short_password(self):
        """Password shorter than 6 characters should be rejected"""
        short_passwords = [
            "",
            "a",
            "abc12",
            "12345",
        ]
        for password in short_passwords:
            result = validate_password_requirements(password)
            self.assertFalse(result, f"Password '{password}' should be rejected (too short)")

    def test_rejects_password_without_numbers(self):
        """Password without numbers should be rejected"""
        no_number_passwords = [
            "abcdef",
            "password",
            "Testing",
        ]
        for password in no_number_passwords:
            result = validate_password_requirements(password)
            self.assertFalse(result, f"Password '{password}' should be rejected (no numbers)")

    def test_rejects_password_without_letters(self):
        """Password without letters should be rejected"""
        no_letter_passwords = [
            "123456",
            "654321",
            "111222",
        ]
        for password in no_letter_passwords:
            result = validate_password_requirements(password)
            self.assertFalse(result, f"Password '{password}' should be rejected (no letters)")

    def test_rejects_common_passwords(self):
        """Common passwords should be rejected"""
        common_passwords = [
            "password",
            "123456",
            "abc123",
            "qwerty",
            "admin",
        ]
        for password in common_passwords:
            result = validate_password_requirements(password)
            self.assertFalse(result, f"Password '{password}' should be rejected (too common)")

    def test_rejects_new_and_old_password_same(self):
        """New password cannot be same as old password"""
        result = validate_password_requirements(
            password="Test123",
            old_password="Test123"
        )
        self.assertFalse(result, "New password should not match old password")

    def test_accepts_different_password_from_old(self):
        """New password different from old password should be accepted"""
        result = validate_password_requirements(
            password="NewPass123",
            old_password="OldPass456"
        )
        self.assertTrue(result, "Different new password should be accepted")


if __name__ == "__main__":
    unittest.main()
