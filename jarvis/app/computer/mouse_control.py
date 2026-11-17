"""
Mouse Controller for NIVA.
Handles single, double, and right clicks, smooth cursor movements, dragging, and scrolling
with screen boundary validation and emergency release handlers.
"""

import logging
import time
from typing import Any, Dict, Literal, Optional, Tuple
import pyautogui

logger = logging.getLogger("NIVA.Mouse")

# PyAutoGUI safety settings
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class MouseController:
    """Provides validated mouse actions."""

    @classmethod
    def get_screen_size(cls) -> Tuple[int, int]:
        return pyautogui.size()

    @classmethod
    def get_position(cls) -> Tuple[int, int]:
        return pyautogui.position()

    @classmethod
    def clamp_coordinates(cls, x: int, y: int) -> Tuple[int, int]:
        """Ensures coordinates stay within physical screen bounds."""
        width, height = pyautogui.size()
        clamped_x = max(0, min(width - 1, int(x)))
        clamped_y = max(0, min(height - 1, int(y)))
        return clamped_x, clamped_y

    @classmethod
    def move_to(cls, x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
        """Moves cursor to coordinates."""
        cx, cy = cls.clamp_coordinates(x, y)
        pyautogui.moveTo(cx, cy, duration=duration)
        return {"success": True, "position": (cx, cy)}

    @classmethod
    def click(
        cls,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Literal["left", "right", "middle"] = "left",
        clicks: int = 1,
        interval: float = 0.1
    ) -> Dict[str, Any]:
        """Performs single, double, or right mouse click."""
        try:
            if x is not None and y is not None:
                cx, cy = cls.clamp_coordinates(x, y)
                pyautogui.click(x=cx, y=cy, clicks=clicks, interval=interval, button=button)
                pos = (cx, cy)
            else:
                pyautogui.click(clicks=clicks, interval=interval, button=button)
                pos = pyautogui.position()

            logger.info(f"Mouse clicked: {button} button, {clicks}x at {pos}")
            return {"success": True, "position": pos, "button": button, "clicks": clicks}
        except Exception as e:
            return {"success": False, "error": f"Mouse click failed: {str(e)}"}

    @classmethod
    def scroll(cls, clicks: int) -> Dict[str, Any]:
        """Scrolls vertically (positive up, negative down)."""
        try:
            pyautogui.scroll(int(clicks))
            return {"success": True, "scroll_amount": clicks}
        except Exception as e:
            return {"success": False, "error": f"Scroll failed: {str(e)}"}

    @classmethod
    def drag_to(cls, x: int, y: int, duration: float = 0.5) -> Dict[str, Any]:
        """Drags mouse to target position."""
        cx, cy = cls.clamp_coordinates(x, y)
        pyautogui.dragTo(cx, cy, duration=duration, button='left')
        return {"success": True, "destination": (cx, cy)}

    @classmethod
    def emergency_release(cls) -> None:
        """Releases held mouse buttons immediately."""
        try:
            pyautogui.mouseUp(button='left')
            pyautogui.mouseUp(button='right')
            pyautogui.mouseUp(button='middle')
        except Exception as e:
            logger.debug(f"Error during emergency mouse release: {e}")

