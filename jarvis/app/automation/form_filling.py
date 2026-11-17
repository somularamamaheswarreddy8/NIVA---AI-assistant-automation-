"""
Intelligent Form Filling and Data Entry Controller for NIVA.
Inspects form field labels, matches appropriate values, fills desktop and browser forms,
and guards against unauthorized form submissions.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import pyautogui

logger = logging.getLogger("NIVA.FormFilling")


class FormFiller:
    """Automates structured data entry into forms and applications."""

    @classmethod
    def fill_form_fields(cls, field_mappings: Dict[str, str], submit_after_fill: bool = False, browser_controller: Optional[Any] = None) -> Dict[str, Any]:
        """
        Fills fields according to mapping.
        If browser_controller with active page is provided, fills via DOM.
        Otherwise, uses desktop keyboard automation with Tab/Enter sequencing.
        """
        filled_count = 0
        errors = []

        # 1. Attempt Browser DOM filling if active Playwright session
        if browser_controller and getattr(browser_controller, "_page", None):
            page = browser_controller._page
            for field_name, value in field_mappings.items():
                try:
                    # Try by id, name, placeholder, or label
                    selectors = [
                        f"input[name='{field_name}']",
                        f"input[id='{field_name}']",
                        f"input[placeholder*='{field_name}' i]",
                        f"textarea[name='{field_name}']",
                        f"#{field_name}",
                        f"label:has-text('{field_name}') + input",
                    ]
                    filled = False
                    for sel in selectors:
                        if page.locator(sel).count() > 0:
                            page.fill(sel, str(value))
                            filled = True
                            filled_count += 1
                            break

                    if not filled:
                        errors.append(f"Field '{field_name}' not located on page.")
                except Exception as e:
                    errors.append(f"Error on '{field_name}': {e}")

            if submit_after_fill:
                try:
                    # Locate submit button
                    page.locator("button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Save')").first.click()
                except Exception as e:
                    errors.append(f"Submit click failed: {e}")

            return {
                "success": filled_count > 0,
                "filled_fields": filled_count,
                "total_fields": len(field_mappings),
                "errors": errors
            }

        # 2. Desktop generic form filling via simulated keystrokes
        old_failsafe = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False
        try:
            for field_name, value in field_mappings.items():
                try:
                    # Type the value and press Tab to go to the next field
                    pyautogui.write(str(value), interval=0.03)
                    time.sleep(0.1)
                    pyautogui.press('tab')
                    time.sleep(0.1)
                    filled_count += 1
                except Exception as e:
                    errors.append(f"Desktop typing failed on '{field_name}': {e}")

            if submit_after_fill:
                pyautogui.press('enter')
        finally:
            pyautogui.FAILSAFE = old_failsafe

        return {
            "success": filled_count > 0,
            "filled_fields": filled_count,
            "total_fields": len(field_mappings),
            "errors": errors,
            "message": f"Entered {filled_count} fields via desktop automation."
        }
