"""
Permission and safety manager for NIVA.
Enforces authorization levels, confirmation prompts for destructive or sensitive actions,
and emergency overrides.
"""

from enum import Enum
import logging
import os
from typing import Any, Callable, Dict, Optional, Set, Tuple

logger = logging.getLogger("NIVA.Safety")

Tuple_Bool_Reason = Tuple[bool, str]


class SafetyLevel(str, Enum):
    SAFE = "SAFE"                 # Read-only or benign actions (open app, search, take screenshot)
    MODERATE = "MODERATE"         # File creation, window manipulation, safe text editing
    SENSITIVE = "SENSITIVE"       # Deleting files, modifying system settings, external form submits
    DANGEROUS = "DANGEROUS"       # Permanent deletion, format drives, system shutdown, financial actions


class PermissionManager:
    """
    Validates tool execution permissions against safety rules.
    If an action is sensitive or dangerous, asks for explicit confirmation via GUI or user prompt.
    """

    # Actions that ALWAYS require explicit user confirmation
    DANGEROUS_ACTIONS: Set[str] = {
        "shutdown_computer",
        "restart_computer",
        "format_drive",
        "delete_permanent",
        "submit_payment",
        "purchase_product",
        "send_email",
        "send_message",
        "execute_arbitrary_shell",
    }

    # Actions that require confirmation when SAFE_MODE is active
    SENSITIVE_ACTIONS: Set[str] = {
        "delete_file",
        "delete_folder",
        "modify_system_setting",
        "submit_web_form",
        "install_software",
        "uninstall_software",
    }

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self._confirmation_callback: Optional[Callable[[str, str], bool]] = None
        self._allowlisted_tools: Set[str] = set()

    def set_confirmation_callback(self, callback: Callable[[str, str], bool]) -> None:
        """Sets GUI confirmation dialog callback: callback(action_title, details_text) -> bool."""
        self._confirmation_callback = callback

    def register_allowlisted_tool(self, tool_name: str) -> None:
        self._allowlisted_tools.add(tool_name)

    def assess_action_safety(self, action_name: str, params: Dict[str, Any]) -> SafetyLevel:
        """Determines the safety category of an action."""
        if action_name in self.DANGEROUS_ACTIONS:
            return SafetyLevel.DANGEROUS

        # Special parameter checks: e.g. permanent file deletion
        if action_name in {"delete_file", "delete_folder"} and params.get("permanent", False):
            return SafetyLevel.DANGEROUS

        if action_name in self.SENSITIVE_ACTIONS:
            return SafetyLevel.SENSITIVE

        # File creation / movement
        if action_name in {"create_file", "write_file", "move_file", "rename_file"}:
            return SafetyLevel.MODERATE

        return SafetyLevel.SAFE

    def check_permission(self, action_name: str, params: Dict[str, Any]) -> Tuple_Bool_Reason:
        """
        Evaluates whether an action is authorized to proceed.
        Returns (allowed: bool, reason: str).
        """
        safety = self.assess_action_safety(action_name, params)

        if safety == SafetyLevel.SAFE:
            return True, "Action classified as SAFE."

        if safety == SafetyLevel.MODERATE:
            return True, "Action classified as MODERATE (auto-permitted)."

        # SENSITIVE or DANGEROUS requires confirmation if safe_mode is ON
        if safety in {SafetyLevel.SENSITIVE, SafetyLevel.DANGEROUS}:
            title = f"Confirmation Required: {action_name}"
            details = f"Action: {action_name}\nParameters: {params}\nSafety Level: {safety.value}"

            if self._confirmation_callback:
                logger.info(f"Prompting user confirmation for {action_name}...")
                approved = self._confirmation_callback(title, details)
                if approved:
                    return True, "User manually approved action."
                else:
                    return False, f"User denied permission for {action_name}."
            else:
                # In head-less / default mode without GUI callback
                if safety == SafetyLevel.DANGEROUS:
                    return False, f"Dangerous action '{action_name}' blocked by safety policy (requires manual user approval)."
                return True, "Sensitive action permitted under current session policy."

        return True, "Authorized."

