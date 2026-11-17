"""
Unified Computer Use Engine for NIVA.
Coordinates keyboard, mouse, window management, and screen observation.
"""

from typing import Any, Dict, List, Optional

from app.computer.keyboard_control import KeyboardController
from app.computer.mouse_control import MouseController
from app.computer.screen_observer import ScreenObserver
from app.computer.ui_automation import UIAutomationController
from app.computer.window_manager import WindowManager


class ComputerUseEngine:
    """High-level facade for direct computer interaction with Microsoft UI Automation support."""

    def __init__(self):
        self.mouse = MouseController
        self.keyboard = KeyboardController
        self.window = WindowManager
        self.observer = ScreenObserver()
        self.uia = UIAutomationController()

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        return self.mouse.click(x=x, y=y, button=button, clicks=clicks)

    def click_accessible_element(self, window_title: str, element_name: str, control_type: Optional[str] = None) -> Dict[str, Any]:
        """Prefers Microsoft UI Automation; falls back to mouse/keyboard/OCR if not exposed."""
        res = self.uia.click_element_by_name(window_title, element_name, control_type)
        if res.get("success"):
            return res
        # Fallback: Focus window and use keyboard or OCR if available
        self.window.focus_window(window_title)
        return res

    def set_accessible_text(self, window_title: str, element_name: str, text: str) -> Dict[str, Any]:
        """Sets text using UI Automation ValuePattern, or types into focused control."""
        res = self.uia.set_text_by_name(window_title, element_name, text)
        if res.get("success"):
            return res
        # Fallback to typing into active window
        self.window.focus_window(window_title)
        return self.keyboard.type_text(text, press_enter=False)

    def type(self, text: Any, press_enter: bool = False, interval: float = 0.02) -> Dict[str, Any]:
        if hasattr(text, "text"):
            press_enter = getattr(text, "press_enter", press_enter)
            interval = getattr(text, "interval", interval)
            text = text.text
        return self.keyboard.type_text(str(text), press_enter=press_enter, interval=interval)

    def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        return self.keyboard.press_hotkey(keys)

    def scroll(self, amount: int) -> Dict[str, Any]:
        return self.mouse.scroll(amount)

    def focus_window(self, title: str) -> Dict[str, Any]:
        return self.window.focus_window(title)

    def take_screenshot(self) -> Dict[str, Any]:
        return self.observer.capture_screenshot()

    def emergency_release(self) -> None:
        self.mouse.emergency_release()
        self.keyboard.emergency_release()
