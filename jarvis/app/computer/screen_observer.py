"""
Screen Observation & Visual Reasoning for NIVA.
Captures desktop screenshots, tracks active application visual states,
and provides OCR text extraction.
"""

from datetime import datetime
import io
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import mss
from PIL import Image

from app.computer.window_manager import WindowManager

logger = logging.getLogger("NIVA.Vision")


class ScreenObserver:
    """Captures and analyzes visual desktop state."""

    def __init__(self, save_dir: Optional[str] = None):
        if not save_dir:
            save_dir = os.path.join(os.path.expanduser("~"), ".niva", "screenshots")
        os.makedirs(save_dir, exist_ok=True)
        self.save_dir = save_dir

    def capture_screenshot(self, region: Optional[List[int]] = None, save_to_disk: bool = True) -> Dict[str, Any]:
        """
        Captures screenshot of entire primary screen or specific bounding box [left, top, width, height].
        """
        try:
            with mss.mss() as sct:
                if region and len(region) == 4:
                    monitor = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
                else:
                    monitor = sct.monitors[1]  # Primary monitor

                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                saved_path = None
                if save_to_disk:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.png"
                    saved_path = os.path.join(self.save_dir, filename)
                    img.save(saved_path, format="PNG")

                active_win = WindowManager.get_active_window()

                return {
                    "success": True,
                    "width": img.width,
                    "height": img.height,
                    "image": img,
                    "saved_path": saved_path,
                    "active_window": active_win.get("title") if active_win else "Unknown"
                }

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return {"success": False, "error": f"Screenshot failed: {str(e)}"}

    def extract_text_from_screen(self, region: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Extracts text from current screen or region using OCR.
        Falls back gracefully if tesseract binary is not installed on system.
        """
        capture_res = self.capture_screenshot(region=region, save_to_disk=False)
        if not capture_res.get("success"):
            return capture_res

        img: Image.Image = capture_res["image"]
        try:
            import pytesseract
            text = pytesseract.image_to_string(img)
            return {
                "success": True,
                "text": text.strip(),
                "active_window": capture_res.get("active_window")
            }
        except Exception as e:
            logger.debug(f"pytesseract OCR unavailable: {e}")
            # Fallback: report active window title and note that OCR binary is not installed
            active_win = capture_res.get("active_window", "Desktop")
            return {
                "success": True,
                "text": f"[Active Window: {active_win}] (Full visual OCR requires Tesseract-OCR binary installed).",
                "active_window": active_win
            }
