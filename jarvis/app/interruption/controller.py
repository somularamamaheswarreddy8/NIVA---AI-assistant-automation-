"""
Dedicated High-Priority Interruption Controller for JARVIS.
Handles real-time STOP, PAUSE, RESUME, OVERRIDE, UNDO, and STATUS commands
without depending on LLM response latency.
"""

from enum import Enum
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config import ASSISTANT_NAME
from app.interruption.cancellation import CancellationToken
from app.interruption.checkpoints import CheckpointManager

logger = logging.getLogger(f"{ASSISTANT_NAME}.Interruption")


class InterruptionCommandType(str, Enum):
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    OVERRIDE = "OVERRIDE"
    UNDO = "UNDO"
    STATUS = "STATUS"
    NONE = "NONE"


class InterruptionController:
    """
    High-priority interruption controller.
    Runs fast regex / keyword matching on any incoming voice or text stream.
    Executes immediate hard-stops, releases hardware hooks, and signals tasks.
    """

    STOP_PATTERNS = [
        r"\b(stop|stop\s+now|shut\s+down|cancel|cancel\s+this|abort|halt|don'?t\s+continue|aapu|aapey|aagandi)\b",
        r"\b(emergency\s+stop|kill\s+task|terminate)\b",
    ]

    PAUSE_PATTERNS = [
        r"\b(pause|wait|hold\s+on|stand\s+by|wait\s+a\s+sec|koncham\s+aagu)\b",
    ]

    RESUME_PATTERNS = [
        r"\b(resume|continue|keep\s+going|carry\s+on|start\s+again|malli\s+chey)\b",
    ]

    UNDO_PATTERNS = [
        r"\b(undo|undo\s+that|revert|revert\s+that|take\s+it\s+back|venakki\s+teesko)\b",
    ]

    STATUS_PATTERNS = [
        r"\b(what\s+are\s+you\s+doing|status|how\s+much\s+(work\s+)?remaining|are\s+you\s+finished|progress)\b",
    ]

    OVERRIDE_PREFIX_PATTERNS = [
        r"^(?:stop|wait|forget\s+that|cancel)[,\.\s]+(?:open|create|search|do|go|start|instead)\b",
        r"\binstead\b",
    ]

    def __init__(self, token: Optional[CancellationToken] = None, checkpoint_mgr: Optional[CheckpointManager] = None):
        self.token = token or CancellationToken()
        self.checkpoint_mgr = checkpoint_mgr or CheckpointManager()
        self.on_stop_callback: Optional[Callable[[], None]] = None
        self.on_pause_callback: Optional[Callable[[], None]] = None
        self.on_resume_callback: Optional[Callable[[], None]] = None
        self.on_override_callback: Optional[Callable[[str], None]] = None
        self.on_status_callback: Optional[Callable[[], str]] = None

    def classify_command(self, text: str) -> Tuple[InterruptionCommandType, Optional[str]]:
        """
        Classifies incoming text into an interruption type.
        Returns (CommandType, extra_payload).
        """
        cleaned = text.strip().lower()

        # Check for OVERRIDE first (e.g. "Stop. Open Notepad instead" or "Forget that. Open Calculator")
        for pattern in self.OVERRIDE_PREFIX_PATTERNS:
            if re.search(pattern, cleaned):
                # Extract the new command part
                # e.g., "stop. open notepad instead" -> "open notepad"
                sub_cmd = re.sub(r"^(?:stop|wait|cancel|forget\s+that|abort)[\s,\.]+", "", cleaned, flags=re.IGNORECASE)
                sub_cmd = re.sub(r"\binstead\b", "", sub_cmd, flags=re.IGNORECASE).strip()
                if sub_cmd:
                    return InterruptionCommandType.OVERRIDE, sub_cmd

        # Check for STOP
        for pattern in self.STOP_PATTERNS:
            if re.search(pattern, cleaned):
                return InterruptionCommandType.STOP, None

        # Check for PAUSE
        for pattern in self.PAUSE_PATTERNS:
            if re.search(pattern, cleaned):
                return InterruptionCommandType.PAUSE, None

        # Check for RESUME
        for pattern in self.RESUME_PATTERNS:
            if re.search(pattern, cleaned):
                return InterruptionCommandType.RESUME, None

        # Check for UNDO
        for pattern in self.UNDO_PATTERNS:
            if re.search(pattern, cleaned):
                return InterruptionCommandType.UNDO, None

        # Check for STATUS
        for pattern in self.STATUS_PATTERNS:
            if re.search(pattern, cleaned):
                return InterruptionCommandType.STATUS, None

        return InterruptionCommandType.NONE, None

    def handle_interruption(self, text: str) -> Tuple[bool, str]:
        """
        Inspects text and immediately executes corresponding control action if matched.
        Returns (handled: bool, response_message: str).
        """
        cmd_type, payload = self.classify_command(text)

        if cmd_type == InterruptionCommandType.STOP:
            self.execute_stop()
            return True, "Task stopped immediately. All pending actions cancelled."

        elif cmd_type == InterruptionCommandType.PAUSE:
            self.execute_pause()
            return True, "Execution paused. Progress preserved."

        elif cmd_type == InterruptionCommandType.RESUME:
            self.execute_resume()
            return True, "Resuming execution from the current step."

        elif cmd_type == InterruptionCommandType.OVERRIDE:
            new_cmd = payload or ""
            self.execute_override(new_cmd)
            return True, f"Previous task aborted. Switching to new command: '{new_cmd}'"

        elif cmd_type == InterruptionCommandType.UNDO:
            result = self.execute_undo()
            return True, result

        elif cmd_type == InterruptionCommandType.STATUS:
            status_msg = self.get_status_message()
            return True, status_msg

        return False, ""

    def execute_stop(self) -> None:
        """Trigger immediate hard stop."""
        logger.warning("INTERRUPTION: STOP triggered!")
        self.token.cancel()
        self._release_hardware_inputs()
        if self.on_stop_callback:
            try:
                self.on_stop_callback()
            except Exception as e:
                logger.error(f"Error in on_stop_callback: {e}")

    def execute_pause(self) -> None:
        """Trigger pause."""
        logger.info("INTERRUPTION: PAUSE triggered.")
        self.token.pause()
        if self.on_pause_callback:
            try:
                self.on_pause_callback()
            except Exception as e:
                logger.error(f"Error in on_pause_callback: {e}")

    def execute_resume(self) -> None:
        """Trigger resume."""
        logger.info("INTERRUPTION: RESUME triggered.")
        self.token.resume()
        if self.on_resume_callback:
            try:
                self.on_resume_callback()
            except Exception as e:
                logger.error(f"Error in on_resume_callback: {e}")

    def execute_override(self, new_command: str) -> None:
        """Stop current task and initiate override."""
        logger.warning(f"INTERRUPTION: OVERRIDE triggered -> {new_command}")
        self.token.cancel()
        self._release_hardware_inputs()
        if self.on_override_callback:
            try:
                self.on_override_callback(new_command)
            except Exception as e:
                logger.error(f"Error in on_override_callback: {e}")

    def execute_undo(self) -> str:
        """Trigger undo of latest reversible action."""
        logger.info("INTERRUPTION: UNDO requested.")
        return self.checkpoint_mgr.undo_last()

    def get_status_message(self) -> str:
        """Retrieve live task status description."""
        if self.on_status_callback:
            try:
                return self.on_status_callback()
            except Exception as e:
                logger.error(f"Error in on_status_callback: {e}")
        return "I am currently idle with no active tasks."

    def _release_hardware_inputs(self) -> None:
        """Emergency release of mouse and keyboard buttons in case an automation was holding them."""
        try:
            import pyautogui
            pyautogui.mouseUp(button='left')
            pyautogui.mouseUp(button='right')
            # Release common modifier keys
            for key in ['ctrl', 'alt', 'shift', 'win']:
                try:
                    pyautogui.keyUp(key)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Input release check: {e}")
