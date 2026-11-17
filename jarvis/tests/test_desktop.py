"""
Tests for Windows Desktop Control: Application resolution, Window enumeration, Mouse coordinates, and Settings.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.automation.application_control import ApplicationController
from app.automation.windows_settings import WindowsSettingsController
from app.computer.mouse_control import MouseController
from app.computer.window_manager import WindowManager


class TestDesktop(unittest.TestCase):

    def test_resolve_executable(self):
        self.assertEqual(ApplicationController.resolve_executable("chrome"), "chrome.exe")
        self.assertEqual(ApplicationController.resolve_executable("notepad"), "notepad.exe")
        self.assertEqual(ApplicationController.resolve_executable("calc"), "calc.exe")
        self.assertEqual(ApplicationController.resolve_executable("vs code"), "code.cmd")

    def test_mouse_coordinates_clamping(self):
        # Clamping within screen bounds
        width, height = MouseController.get_screen_size()
        cx, cy = MouseController.clamp_coordinates(-100, -50)
        self.assertEqual(cx, 0)
        self.assertEqual(cy, 0)

        cx, cy = MouseController.clamp_coordinates(99999, 99999)
        self.assertEqual(cx, width - 1)
        self.assertEqual(cy, height - 1)

    def test_list_open_windows(self):
        windows = WindowManager.list_open_windows()
        self.assertIsInstance(windows, list)
        # On a running desktop system, there are almost always top-level windows
        for w in windows:
            self.assertIn("title", w)
            self.assertIn("width", w)

    def test_settings_pages_mapped(self):
        pages = ["bluetooth", "wifi", "sound", "display", "windows_update", "control_panel"]
        for p in pages:
            self.assertIn(p, WindowsSettingsController.SETTINGS_PAGES)


if __name__ == "__main__":
    unittest.main()
