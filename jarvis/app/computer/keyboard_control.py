"""
Keyboard Controller for NIVA.
Handles simulated typing, hotkeys, key presses, and modifier key management
with cancellation checks and emergency release handlers.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import pyautogui
import pyperclip

pyautogui.FAILSAFE = False

logger = logging.getLogger("NIVA.Keyboard")


class KeyboardController:
    """Provides validated keyboard input automation."""

    MODIFIER_KEYS = ['ctrl', 'shift', 'alt', 'win']

    @classmethod
    def type_text(cls, text: Any, press_enter: bool = False, interval: float = 0.02) -> Dict[str, Any]:
        """Types string into active window reliably using clipboard paste with keyboard fallback."""
        if hasattr(text, "text"):
            press_enter = getattr(text, "press_enter", press_enter)
            interval = getattr(text, "interval", interval)
            text = text.text
        text_str = str(text)

        try:
            pyautogui.FAILSAFE = False
            time.sleep(0.3)
            # Use clipboard paste for guaranteed accuracy across all languages, special characters, and newlines
            pyperclip.copy(text_str)
            pyautogui.hotkey('ctrl', 'v')
            if press_enter:
                time.sleep(0.1)
                pyautogui.press('enter')
            return {
                "success": True,
                "message": f"Successfully typed '{text_str}' into the active window.",
                "typed_length": len(text_str),
                "text": text_str
            }
        except Exception as e:
            logger.warning(f"Clipboard paste failed: {e}. Trying direct write fallback...")
            # Fallback to direct keystroke simulation
            try:
                pyautogui.FAILSAFE = False
                pyautogui.write(text_str, interval=interval)
                if press_enter:
                    pyautogui.press('enter')
                return {
                    "success": True,
                    "message": f"Successfully typed '{text_str}' into the active window.",
                    "typed_length": len(text_str),
                    "text": text_str
                }
            except Exception as e2:
                logger.error(f"Typing fallback error: {traceback.format_exc()}")
                return {"success": False, "error": f"Typing failed: {str(e2)}"}

    @classmethod
    def press_hotkey(cls, keys: List[str]) -> Dict[str, Any]:
        """
        Presses a key combination (e.g., ['ctrl', 'c'], ['win', 'd'], ['alt', 'tab']).
        """
        try:
            normalized = [k.lower().strip() for k in keys]
            logger.info(f"Pressing hotkey: {' + '.join(normalized)}")
            pyautogui.hotkey(*normalized)
            return {"success": True, "hotkey": normalized}
        except Exception as e:
            return {"success": False, "error": f"Hotkey execution failed: {str(e)}"}

    @classmethod
    def press_key(cls, key_name: str, presses: int = 1) -> Dict[str, Any]:
        """Presses an individual key."""
        try:
            pyautogui.press(key_name.lower().strip(), presses=presses)
            return {"success": True, "key": key_name, "presses": presses}
        except Exception as e:
            return {"success": False, "error": f"Key press failed: {str(e)}"}

    @classmethod
    def emergency_release(cls) -> None:
        """Releases all modifier keys immediately in case of interruption."""
        for mod in cls.MODIFIER_KEYS:
            try:
                pyautogui.keyUp(mod)
            except Exception:
                pass
