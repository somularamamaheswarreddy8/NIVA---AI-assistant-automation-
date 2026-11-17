"""
Validation and sanitization utilities for files, commands, and inputs.
"""

import os
from pathlib import Path
import re
from typing import List, Optional, Tuple


class PathValidator:
    """Guards against unauthorized filesystem operations on Windows system directories."""

    RESTRICTED_SYSTEM_PATHS: List[str] = [
        os.environ.get("SystemRoot", r"C:\Windows"),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64"),
        r"C:\Boot",
        r"C:\Recovery",
    ]

    @classmethod
    def is_safe_path(cls, target_path: str, for_writing: bool = False) -> Tuple[bool, str]:
        """
        Ensures target path does not violate Windows integrity.
        """
        try:
            resolved = Path(target_path).resolve()
            resolved_str = str(resolved).lower()

            # Prevent dangerous root drives or system folders modification
            if for_writing:
                for restricted in cls.RESTRICTED_SYSTEM_PATHS:
                    if restricted and resolved_str.startswith(restricted.lower()):
                        return False, f"Access denied: Path is inside restricted system directory ({restricted})."

                # Check if trying to delete or format root drive
                if resolved_str in [r"c:\\", r"c:", r"d:\\", r"d:"]:
                    return False, "Access denied: Root drive deletion/formatting is forbidden."

            return True, "Path validated successfully."

        except Exception as e:
            return False, f"Invalid path syntax: {e}"

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Removes illegal Windows filename characters."""
        return re.sub(r'[<>:"/\\|?*]', '_', filename).strip()


class CommandValidator:
    """Validates application and command invocations."""

    BLOCKED_SHELL_PATTERNS = [
        r"\bformat\s+[a-z]:",
        r"\brmdir\s+/s\s+/q\s+c:\\",
        r"\bdel\s+/[sfq]\s+c:\\",
        r"\bshutdown\s+/[sr]",
        r"\bvssadmin\s+delete\s+shadows",
        r"\bbcdedit",
    ]

    @classmethod
    def is_safe_command(cls, command_str: str) -> Tuple[bool, str]:
        cmd_lower = command_str.lower().strip()
        for pattern in cls.BLOCKED_SHELL_PATTERNS:
            if re.search(pattern, cmd_lower):
                return False, f"Blocked potentially destructive command pattern: {pattern}"
        return True, "Command is safe."
