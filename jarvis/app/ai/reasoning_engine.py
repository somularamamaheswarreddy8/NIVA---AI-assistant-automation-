"""
Reasoning and Plan Adaptation Engine for NIVA.
Evaluates step outcomes, handles dynamic error recovery, and verifies final task goals.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIVA.Reasoning")

Tuple_Bool_Action = Tuple[bool, Optional[str]]


class ReasoningEngine:
    """Provides plan verification, error analysis, and goal validation."""

    @classmethod
    def evaluate_step_outcome(cls, step_dict: Dict[str, Any], result: Dict[str, Any]) -> Tuple_Bool_Action:
        """
        Determines whether the step succeeded and what corrective action is needed if it failed.
        Returns (is_successful: bool, corrective_action: Optional[str]).
        """
        success = result.get("success", False)

        if success:
            return True, None

        error_msg = str(result.get("error", "Unknown error")).lower()
        tool_name = step_dict.get("tool_name", "")

        logger.warning(f"Step failed ({tool_name}): {error_msg}")

        # Recovery strategy 1: Browser launch failed -> fallback to system default browser
        if tool_name == "browser_open" and "playwright" in error_msg:
            return False, "retry_with_system_browser"

        # Recovery strategy 2: Application not found -> search in common paths or open Start Menu
        if tool_name == "launch_app" and "not found" in error_msg:
            return False, "search_start_menu"

        # Recovery strategy 3: File permission error -> prompt user for permission or alternative directory
        if "permission" in error_msg or "access is denied" in error_msg:
            return False, "request_user_elevation"

        return False, "abort_or_ask"

