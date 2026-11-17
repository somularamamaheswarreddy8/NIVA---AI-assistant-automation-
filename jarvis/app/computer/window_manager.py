"""
Windows Window Manager for NIVA.
Discovers, enumerates, focuses, minimizes, maximizes, and restores desktop application windows
using pygetwindow, ctypes user32, and keyboard shortcuts.
"""

import ctypes
from ctypes import wintypes
import logging
import time
from typing import Any, Dict, List, Optional
import pygetwindow as gw
import pyautogui
import psutil

logger = logging.getLogger("NIVA.WindowManager")

try:
    user32 = ctypes.windll.user32
except Exception:
    user32 = None


class WindowManager:
    """Controls and inspects open Windows application windows."""

    @staticmethod
    def _attach_thread_desktop() -> None:
        """Attaches calling thread to interactive desktop session if possible."""
        if user32:
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

    @classmethod
    def get_active_window(cls) -> Optional[Dict[str, Any]]:
        """Returns details of the currently focused active window."""
        cls._attach_thread_desktop()
        try:
            win = gw.getActiveWindow()
            if win and win.title:
                return {
                    "title": win.title,
                    "x": win.left,
                    "y": win.top,
                    "width": win.width,
                    "height": win.height,
                    "is_active": win.isActive,
                    "is_maximized": win.isMaximized,
                    "is_minimized": win.isMinimized
                }
        except Exception as e:
            logger.debug(f"Could not retrieve active window: {e}")
        return None

    @classmethod
    def list_open_windows(cls) -> List[Dict[str, Any]]:
        """Lists all visible top-level windows with non-empty titles."""
        cls._attach_thread_desktop()
        result = []

        # 1. First attempt via pygetwindow
        try:
            windows = gw.getAllWindows()
            for w in windows:
                if w.title and w.visible and w.width > 50 and w.height > 50:
                    result.append({
                        "title": w.title,
                        "x": w.left,
                        "y": w.top,
                        "width": w.width,
                        "height": w.height,
                        "is_active": w.isActive,
                        "is_minimized": w.isMinimized
                    })
        except Exception as e:
            logger.error(f"Error listing windows via pygetwindow: {e}")

        if result:
            return result

        # 2. Fallback to direct win32 EnumDesktopWindows
        if user32:
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                def enum_cb(hwnd, lparam):
                    if not user32.IsWindowVisible(hwnd):
                        return True
                    style = user32.GetWindowLongW(hwnd, -16)
                    if style & 0x40000000:
                        return True
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if w < 50 or h < 50:
                        return True
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        if buff.value.strip():
                            result.append({
                                "title": buff.value,
                                "x": rect.left,
                                "y": rect.top,
                                "width": w,
                                "height": h,
                                "is_active": False,
                                "is_minimized": bool(user32.IsIconic(hwnd)),
                                "hwnd": hwnd
                            })
                    return True

                cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb)
                if hdesk:
                    user32.EnumDesktopWindows(hdesk, cb, 0)
                else:
                    user32.EnumWindows(cb, 0)
            except Exception as e:
                logger.error(f"Error enumerating windows via ctypes: {e}")

        return result

    @classmethod
    def find_windows(cls, title_substring: str) -> List[Any]:
        """Finds window objects matching a title substring or application process name."""
        cls._attach_thread_desktop()
        sub = title_substring.lower().strip()
        all_wins = []
        try:
            all_wins = gw.getAllWindows()
        except Exception:
            pass
        matches = [w for w in all_wins if w.title and sub in w.title.lower()]
        return matches

    @classmethod
    def is_window_visible_on_screen(cls, target_name: str) -> bool:
        """Checks if a visible, non-minimized window exists for application or title."""
        cls._attach_thread_desktop()
        sub = target_name.lower().strip()

        # Check pygetwindow first
        try:
            for w in gw.getAllWindows():
                if w.title and sub in w.title.lower() and w.visible and not w.isMinimized:
                    return True
        except Exception:
            pass

        # Check via win32 APIs
        if user32:
            target_pids = set()
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if sub in pname or sub.replace(' ', '') in pname:
                        target_pids.add(p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            found = [False]
            def enum_cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                if user32.IsIconic(hwnd):
                    return True
                style = user32.GetWindowLongW(hwnd, -16)
                if style & 0x40000000:
                    return True
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if (rect.right - rect.left) < 50 or (rect.bottom - rect.top) < 50:
                    return True

                lp_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lp_pid))
                if target_pids and lp_pid.value in target_pids:
                    found[0] = True
                    return False
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if sub in buff.value.lower():
                        found[0] = True
                        return False
                return True

            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb)
                if hdesk:
                    user32.EnumDesktopWindows(hdesk, cb, 0)
                else:
                    user32.EnumWindows(cb, 0)
            except Exception:
                pass

            return found[0]

        return False

    @classmethod
    def focus_window(cls, title_substring: str) -> Dict[str, Any]:
        """Brings the matching window to the foreground and unminimizes it."""
        cls._attach_thread_desktop()
        sub = title_substring.lower().strip()

        # 1. Try pygetwindow match
        matches = cls.find_windows(title_substring)
        if matches:
            target = matches[0]
            try:
                if target.isMinimized:
                    target.restore()
                target.activate()
                time.sleep(0.3)
                return {"success": True, "message": f"Focused window: '{target.title}'", "title": target.title}
            except Exception as e:
                logger.debug(f"pygetwindow activate failed: {e}")

        # 2. Fallback to win32 HWND resolution (matches title OR process name)
        if user32:
            target_pids = set()
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if sub in pname or sub.replace(' ', '') in pname:
                        target_pids.add(p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            found_hwnds = []
            def enum_cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                style = user32.GetWindowLongW(hwnd, -16)
                if style & 0x40000000:
                    return True
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if (rect.right - rect.left) < 50 or (rect.bottom - rect.top) < 50:
                    return True

                lp_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lp_pid))
                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value

                matched = False
                if target_pids and lp_pid.value in target_pids:
                    matched = True
                elif title and sub in title.lower():
                    matched = True

                if matched:
                    found_hwnds.append((hwnd, title))
                return True

            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb)
                if hdesk:
                    user32.EnumDesktopWindows(hdesk, cb, 0)
                else:
                    user32.EnumWindows(cb, 0)
            except Exception as e:
                logger.error(f"Error enumerating windows for focus: {e}")

            if found_hwnds:
                hwnd, win_title = found_hwnds[0]
                try:
                    if user32.IsIconic(hwnd):
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.ShowWindow(hwnd, 5)      # SW_SHOW
                    # Simulate Alt key to bypass Windows SetForegroundWindow restriction
                    try:
                        user32.keybd_event(0x12, 0, 0, 0)
                        user32.keybd_event(0x12, 0, 2, 0)
                    except Exception:
                        pass
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    time.sleep(0.3)
                    display_title = win_title or title_substring
                    return {"success": True, "message": f"Focused window: '{display_title}'", "title": display_title}
                except Exception as e:
                    return {"success": False, "error": f"Failed to activate window: {str(e)}"}

        return {"success": False, "error": f"No window matching '{title_substring}' was found."}

    @classmethod
    def ensure_visible(cls, app_or_title: str) -> Dict[str, Any]:
        """Ensures an application window is unminimized and visible in foreground."""
        return cls.focus_window(app_or_title)

    @classmethod
    def control_window(cls, title_substring: Optional[str], action: str = "focus") -> Dict[str, Any]:
        """Performs focus, minimize, maximize, restore, or close on a window."""
        action = action.lower()

        # If no title given, operate on the active window
        if not title_substring:
            win = gw.getActiveWindow()
            if not win:
                return {"success": False, "error": "No active window found."}
            target = win
        else:
            matches = cls.find_windows(title_substring)
            if not matches:
                # Try focus_window fallback for focus/restore
                if action in ["focus", "restore"]:
                    return cls.focus_window(title_substring)
                return {"success": False, "error": f"No window matching '{title_substring}' found."}
            target = matches[0]

        try:
            if action == "focus":
                if target.isMinimized:
                    target.restore()
                target.activate()
            elif action == "minimize":
                target.minimize()
            elif action == "maximize":
                target.maximize()
            elif action == "restore":
                target.restore()
            elif action == "close":
                target.close()
            else:
                return {"success": False, "error": f"Unknown window action '{action}'"}

            return {"success": True, "message": f"Successfully performed '{action}' on '{target.title}'."}

        except Exception as e:
            return {"success": False, "error": f"Error performing '{action}' on window: {str(e)}"}

    @classmethod
    def show_desktop(cls) -> Dict[str, Any]:
        """Toggles Show Desktop (Win + D)."""
        try:
            pyautogui.hotkey('win', 'd')
            return {"success": True, "message": "Triggered Show Desktop (Win+D)"}
        except Exception as e:
            return {"success": False, "error": f"Show desktop failed: {str(e)}"}

