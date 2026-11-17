"""
Tests for Safety, Permission Enforcement, Path Validation, and Audit Logging in JARVIS.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.safety.audit_log import AuditLogger
from app.safety.permissions import PermissionManager, SafetyLevel
from app.safety.validation import CommandValidator, PathValidator


class TestSafety(unittest.TestCase):

    def setUp(self):
        self.permissions = PermissionManager(safe_mode=True)
        self.audit = AuditLogger()

    def test_restricted_system_path_blocked(self):
        system32_path = r"C:\Windows\System32\malicious.dll"
        is_safe, reason = PathValidator.is_safe_path(system32_path, for_writing=True)
        self.assertFalse(is_safe)
        self.assertIn("restricted system directory", reason)

    def test_safe_user_path_allowed(self):
        user_path = os.path.join(os.path.expanduser("~"), "Desktop", "my_file.txt")
        is_safe, reason = PathValidator.is_safe_path(user_path, for_writing=True)
        self.assertTrue(is_safe)

    def test_command_validator_blocks_destructive_shell(self):
        destructive_cmd = "format c: /fs:ntfs"
        safe, reason = CommandValidator.is_safe_command(destructive_cmd)
        self.assertFalse(safe)

    def test_safety_level_assessment(self):
        self.assertEqual(
            self.permissions.assess_action_safety("shutdown_computer", {}),
            SafetyLevel.DANGEROUS
        )
        self.assertEqual(
            self.permissions.assess_action_safety("delete_file", {"permanent": True}),
            SafetyLevel.DANGEROUS
        )
        self.assertEqual(
            self.permissions.assess_action_safety("create_file", {}),
            SafetyLevel.MODERATE
        )
        self.assertEqual(
            self.permissions.assess_action_safety("capture_screen", {}),
            SafetyLevel.SAFE
        )

    def test_user_confirmation_callback(self):
        # Simulate user denying permission
        self.permissions.set_confirmation_callback(lambda title, details: False)
        allowed, reason = self.permissions.check_permission("delete_file", {"path": "test.txt"})
        self.assertFalse(allowed)

        # Simulate user granting permission
        self.permissions.set_confirmation_callback(lambda title, details: True)
        allowed, reason = self.permissions.check_permission("delete_file", {"path": "test.txt"})
        self.assertTrue(allowed)

    def test_audit_logger(self):
        entry = self.audit.log("create_file", "test.txt", {"path": "test.txt"}, status="SUCCESS")
        self.assertEqual(entry.action_type, "create_file")
        recent = self.audit.get_recent(5)
        self.assertGreaterEqual(len(recent), 1)


if __name__ == "__main__":
    unittest.main()
