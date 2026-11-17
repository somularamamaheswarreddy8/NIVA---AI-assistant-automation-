"""
Microsoft UI Automation Controller for NIVA.
Provides accessible desktop automation using Windows UI Automation (UIA) technology.
Prefers accessible element names, control types, and UIA patterns over brittle screen coordinates.
Falls back safely to OCR or keyboard/mouse interaction when an application does not expose accessible UIA elements.
"""

import ctypes
import logging
import re
import time
from typing import Any, Dict, List, Optional
import pywinauto
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

from app.config import ASSISTANT_NAME

logger = logging.getLogger(f"{ASSISTANT_NAME}.UIAutomation")

try:
    user32 = ctypes.windll.user32
except Exception:
    user32 = None


class UIAutomationController:
    """Interacts with Windows desktop applications using Microsoft UI Automation (UIA)."""

    def __init__(self):
        self._desktop = None

    @staticmethod
    def _attach_thread_desktop() -> None:
        """Attaches calling thread to interactive desktop session."""
        if user32:
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

    def _get_desktop(self) -> Desktop:
        self._attach_thread_desktop()
        if self._desktop is None:
            self._desktop = Desktop(backend="uia")
        return self._desktop

    def find_window(self, title_substring: Optional[str] = None, timeout: float = 3.0):
        """Connects to a top-level window matching title_substring via UIA, or active window if empty."""
        self._attach_thread_desktop()
        desktop = self._get_desktop()

        if not title_substring:
            # 1. Try to get active window
            try:
                from app.computer.window_manager import WindowManager
                act = WindowManager.get_active_window()
                if act and act.get("title"):
                    for w in desktop.windows():
                        try:
                            if act["title"].lower() in w.window_text().lower():
                                return w
                        except Exception:
                            continue
            except Exception:
                pass

            # 2. Return first visible top-level application window
            for w in desktop.windows():
                try:
                    txt = w.window_text()
                    if txt and txt not in ["Taskbar", "Program Manager"] and w.is_visible():
                        return w
                except Exception:
                    continue
            return None

        # Look up by title substring
        try:
            app = pywinauto.Application(backend="uia").connect(title_re=f".*{re.escape(title_substring)}.*", timeout=timeout)
            return app.top_window()
        except Exception:
            try:
                for w in desktop.windows():
                    try:
                        if title_substring.lower() in w.window_text().lower():
                            return w
                    except Exception:
                        continue
            except Exception:
                pass
        return None

    def list_accessible_elements(self, window_title: str, max_count: int = 30) -> Dict[str, Any]:
        """
        Enumerates accessible child controls (Buttons, Edits, Text, Checkboxes)
        in the specified window using Microsoft UI Automation.
        """
        win = self.find_window(window_title)
        if not win:
            return {"success": False, "error": f"Window matching '{window_title}' not found via UI Automation."}

        elements = []
        try:
            for child in win.descendants():
                try:
                    name = child.window_text().strip()
                    ctrl_type = child.friendly_class_name()
                    auto_id = getattr(child.element_info, "automation_id", "")
                    if name and len(name) < 100:
                        elements.append({
                            "name": name,
                            "control_type": ctrl_type,
                            "automation_id": auto_id,
                            "is_enabled": child.is_enabled(),
                            "is_visible": child.is_visible()
                        })
                        if len(elements) >= max_count:
                            break
                except Exception:
                    continue

            return {
                "success": True,
                "window": window_title,
                "element_count": len(elements),
                "elements": elements
            }
        except Exception as e:
            logger.error(f"Error enumerating UIA elements in '{window_title}': {e}")
            return {"success": False, "error": str(e)}

    def click_element_by_name(self, window_title: Optional[str] = None, element_name: str = "", control_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Finds and clicks an accessible control (button, menu, checkbox) by its accessible name.
        Uses UIA InvokePattern first, falling back to click_input().
        If window_title is empty, searches the active application window or top desktop windows.
        """
        self._attach_thread_desktop()
        win = self.find_window(window_title)

        candidate_windows = [win] if win else []
        if not candidate_windows:
            desktop = self._get_desktop()
            for w in desktop.windows():
                try:
                    if w.is_visible() and w.window_text() not in ["Program Manager"]:
                        candidate_windows.append(w)
                except Exception:
                    pass

        if not candidate_windows:
            return {"success": False, "error": f"No accessible window available to click '{element_name}'."}

        target = None
        target_sub = element_name.lower().strip()
        matched_window = None

        for w in candidate_windows:
            try:
                for child in w.descendants():
                    try:
                        txt = child.window_text().lower().strip()
                        auto_id = getattr(child.element_info, "automation_id", "").lower().strip()
                        if target_sub == txt or (target_sub in txt and len(txt) - len(target_sub) < 15) or (target_sub and target_sub in auto_id):
                            if control_type:
                                if control_type.lower() in child.friendly_class_name().lower():
                                    target = child
                                    matched_window = w
                                    break
                            else:
                                target = child
                                matched_window = w
                                break
                    except Exception:
                        continue
                if target:
                    break
            except Exception:
                continue

        if not target:
            win_name = window_title or (matched_window.window_text() if matched_window else "active window")
            return {
                "success": False,
                "error": f"Accessible UI element '{element_name}' was not found in {win_name}."
            }

        # Click or invoke the element
        try:
            matched_name = target.window_text() or element_name
            try:
                target.invoke()
                logger.info(f"UIA: Successfully invoked element '{matched_name}' via InvokePattern.")
                return {"success": True, "message": f"Clicked '{matched_name}' via UIA InvokePattern.", "element": matched_name}
            except Exception:
                target.click_input()
                logger.info(f"UIA: Successfully clicked element '{matched_name}' via click_input.")
                return {"success": True, "message": f"Clicked '{matched_name}' via UIA click_input.", "element": matched_name}

        except Exception as e:
            logger.error(f"UIA click failed for '{element_name}': {e}")
            return {"success": False, "error": f"UI Automation click error: {str(e)}"}

    def set_text_by_name(self, window_title: str, element_name: str, text: str) -> Dict[str, Any]:
        """
        Enters text into an accessible Edit or Input control using UI Automation ValuePattern.
        """
        win = self.find_window(window_title)
        if not win:
            return {"success": False, "error": f"Window '{window_title}' not found."}

        try:
            target = None
            target_sub = element_name.lower().strip()

            for child in win.descendants(control_type="Edit"):
                try:
                    txt = child.window_text().lower().strip()
                    auto_id = getattr(child.element_info, "automation_id", "").lower()
                    if target_sub in txt or target_sub in auto_id:
                        target = child
                        break
                except Exception:
                    continue

            # If no named edit found, check first edit control if element_name is generic
            if not target and element_name.lower() in ["input", "textbox", "edit", "field", "text"]:
                edits = win.descendants(control_type="Edit")
                if edits:
                    target = edits[0]

            if not target:
                return {"success": False, "error": f"Accessible text field '{element_name}' not found."}

            try:
                target.set_edit_text(text)
                logger.info(f"UIA: Successfully set text via set_edit_text in '{element_name}'.")
                return {"success": True, "message": f"Entered text via UIA ValuePattern into '{element_name}'.", "method": "uia_set_edit_text"}
            except Exception:
                target.click_input()
                target.type_keys(text, with_spaces=True)
                return {"success": True, "message": f"Typed text via UIA into '{element_name}'.", "method": "uia_type_keys"}

        except Exception as e:
            return {"success": False, "error": f"UI Automation set_text error: {str(e)}"}

    def get_element_text(self, window_title: str, element_name: str) -> Dict[str, Any]:
        """Reads text from an accessible UI element."""
        win = self.find_window(window_title)
        if not win:
            return {"success": False, "error": f"Window '{window_title}' not found."}

        try:
            target_sub = element_name.lower().strip()
            for child in win.descendants():
                try:
                    txt = child.window_text()
                    if target_sub in txt.lower():
                        return {"success": True, "text": txt, "element": element_name}
                except Exception:
                    continue
            return {"success": False, "error": f"Element '{element_name}' not found."}
        except Exception as e:
            return {"success": False, "error": str(e)}
