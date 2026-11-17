import ast
import ctypes
import logging
import operator
import re
import subprocess
import time
from typing import Any, Dict, Optional, Union
import win32con
import win32gui
import pywinauto

logger = logging.getLogger("NIVA.Calculator")

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000
}


def safe_eval_math(expression: str) -> Union[int, float]:
    """Safely evaluates arithmetic expressions without using unrestricted eval()."""
    expr = expression.strip()
    if not expr:
        raise ValueError("Empty mathematical expression")

    expr = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1 * \2", expr)
    tree = ast.parse(expr, mode='eval')

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        elif hasattr(ast, "Num") and isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type}")
            operand = _eval_node(node.operand)
            return SAFE_OPERATORS[op_type](operand)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type}")
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if op_type is ast.Pow and abs(right) > 1000:
                raise OverflowError("Exponent too large for safe evaluation")
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero")
            return SAFE_OPERATORS[op_type](left, right)
        else:
            raise ValueError(f"Unsupported syntax in math expression: {type(node).__name__}")

    res = _eval_node(tree)
    if isinstance(res, float) and res.is_integer():
        return int(res)
    return res


def parse_math_phrase(phrase: str) -> Optional[str]:
    """Translates spoken or typed natural language math phrases into clean arithmetic expressions."""
    text = phrase.strip().lower()
    text = text.rstrip("?!.;")

    # Strip conversational prefixes
    text = re.sub(r"^(?:please\s+)?(?:can\s+you\s+)?(?:what\s+is|calculate|compute|solve|eval|evaluate)\s+", "", text).strip()
    text = re.sub(r"^(?:the\s+)?(?:result\s+of|value\s+of)\s+", "", text).strip()

    # Pattern: "subtract X from Y" -> "Y - X"
    m_sub_from = re.match(r"^subtract\s+([\d\.\-]+)\s+from\s+([\d\.\-]+)$", text)
    if m_sub_from:
        return f"{m_sub_from.group(2)} - {m_sub_from.group(1)}"

    # Pattern: "divide X by Y" -> "X / Y"
    m_div_by = re.match(r"^divide\s+([\d\.\-]+)\s+by\s+([\d\.\-]+)$", text)
    if m_div_by:
        return f"{m_div_by.group(1)} / {m_div_by.group(2)}"

    # Pattern: "multiply X by Y" / "multiply X and Y" -> "X * Y"
    m_mul_by = re.match(r"^multiply\s+([\d\.\-]+)\s+(?:by|with|and)\s+([\d\.\-]+)$", text)
    if m_mul_by:
        return f"{m_mul_by.group(1)} * {m_mul_by.group(2)}"

    # Pattern: "add X and Y" / "add X to Y" / "add X plus Y"
    m_add_and = re.match(r"^add\s+([\d\.\-]+)\s+(?:and|to|plus)\s+([\d\.\-]+)$", text)
    if m_add_and:
        return f"{m_add_and.group(1)} + {m_add_and.group(2)}"

    # Pattern: "add X+Y" / "add 2+2"
    m_add_expr = re.match(r"^add\s+([0-9\s\+\-\*\/\(\)\.]+)$", text)
    if m_add_expr:
        return m_add_expr.group(1).strip()

    # Replace "negative" before a digit with "-"
    text = re.sub(r"\bnegative\s+(\d)", r"-\1", text)

    # Standard natural language replacements:
    text = re.sub(r"\b(?:times|multiplied\s+by)\b", "*", text)
    text = re.sub(r"\b(?:divided\s+by|over)\b", "/", text)
    text = re.sub(r"\bplus\b", "+", text)
    text = re.sub(r"\bminus\b", "-", text)

    # Convert simple number words
    words = text.split()
    converted_words = []
    for w in words:
        if w in WORD_TO_NUM:
            converted_words.append(str(WORD_TO_NUM[w]))
        else:
            converted_words.append(w)
    text = " ".join(converted_words)

    clean = re.sub(r"\s+", " ", text).strip()
    if re.search(r"\d", clean) and re.search(r"[\+\-\*\/\%]", clean):
        if re.match(r"^[0-9\s\+\-\*\/\%\(\)\.]+$", clean):
            return clean

    return None


class CalculatorAutomation:
    """Automates and verifies calculations directly inside Windows Calculator."""

    @staticmethod
    def _attach_thread_desktop():
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception as e:
            logger.debug(f"Desktop attach exception: {e}")

    @classmethod
    def find_calculator_window(cls, auto_launch: bool = False) -> Optional[int]:
        """Finds top-level ApplicationFrameWindow for Calculator."""
        cls._attach_thread_desktop()

        found_hwnds = []
        def enum_cb(h, _):
            if win32gui.IsWindowVisible(h):
                cls_name = win32gui.GetClassName(h)
                txt = win32gui.GetWindowText(h)
                if cls_name == "ApplicationFrameWindow" and "calculator" in txt.lower():
                    found_hwnds.append(h)

        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
        if hdesk:
            win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
        else:
            win32gui.EnumWindows(enum_cb, None)

        if found_hwnds:
            return found_hwnds[0]

        if auto_launch:
            subprocess.Popen(["calc.exe"])
            for _ in range(15):
                time.sleep(0.2)
                found_hwnds.clear()
                if hdesk:
                    win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
                else:
                    win32gui.EnumWindows(enum_cb, None)
                if found_hwnds:
                    return found_hwnds[0]

        return None

    @classmethod
    def calculate(cls, expression_or_phrase: str, ensure_open: bool = True) -> Dict[str, Any]:
        """
        Parses expression, enters it into Windows Calculator, verifies display,
        and cross-checks against safe AST evaluation.
        """
        parsed_expr = parse_math_phrase(expression_or_phrase)
        if not parsed_expr:
            # Check if it's already a clean math expression
            clean = expression_or_phrase.strip()
            if re.match(r"^[0-9\s\+\-\*\/\%\(\)\.]+$", clean):
                parsed_expr = clean
            else:
                return {
                    "success": False,
                    "error": f"Could not parse valid mathematical expression from '{expression_or_phrase}'."
                }

        # Safe AST Evaluation
        try:
            expected_result = safe_eval_math(parsed_expr)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid math expression '{parsed_expr}': {str(e)}"
            }

        # Check / connect Calculator
        hwnd = cls.find_calculator_window(auto_launch=ensure_open)
        if not hwnd:
            return {
                "success": False,
                "in_calculator": False,
                "result": expected_result,
                "error": "Windows Calculator is not open or could not be launched.",
                "message": f"Windows Calculator is not open. Safe evaluation result: {expected_result}"
            }

        try:
            # Bring window to foreground
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.2)

            app = pywinauto.Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)

            # Clear previous calculations
            try:
                win.child_window(auto_id="clearButton").invoke()
            except Exception:
                try:
                    win.child_window(auto_id="clearEntryButton").invoke()
                except Exception:
                    pass

            time.sleep(0.1)

            # Map characters to UIA buttons
            BTN_MAP = {
                "0": "num0Button", "1": "num1Button", "2": "num2Button", "3": "num3Button",
                "4": "num4Button", "5": "num5Button", "6": "num6Button", "7": "num7Button",
                "8": "num8Button", "9": "num9Button",
                "+": "plusButton", "-": "minusButton", "*": "multiplyButton", "/": "divideButton",
                ".": "decimalSeparatorButton", "=": "equalButton"
            }

            tokens = re.findall(r"\d+|[\+\-\*\/\.\=]", parsed_expr)
            for tok in tokens:
                if tok.isdigit():
                    for ch in tok:
                        win.child_window(auto_id=BTN_MAP[ch]).invoke()
                elif tok in BTN_MAP:
                    win.child_window(auto_id=BTN_MAP[tok]).invoke()
                time.sleep(0.05)

            # Equals
            win.child_window(auto_id="equalButton").invoke()
            time.sleep(0.3)

            # Read result from CalculatorResults
            res_ctrl = win.child_window(auto_id="CalculatorResults")
            res_text = res_ctrl.window_text()  # e.g., "Display is 4"
            logger.info(f"Calculator display raw text: '{res_text}'")

            # Extract displayed number
            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", res_text.replace(",", ""))
            displayed_val = None
            if m:
                val_str = m.group(0)
                displayed_val = float(val_str) if "." in val_str else int(val_str)

            # Verification
            is_verified = (displayed_val == expected_result) if displayed_val is not None else False

            return {
                "success": True,
                "in_calculator": True,
                "expression": parsed_expr,
                "result": expected_result,
                "displayed_result": displayed_val,
                "verified": is_verified,
                "message": f"Calculated {parsed_expr} in Calculator. Display shows: {displayed_val}."
            }

        except Exception as e:
            logger.error(f"Error automating Calculator app: {e}")
            return {
                "success": False,
                "in_calculator": False,
                "result": expected_result,
                "error": f"Calculator automation failed: {str(e)}",
                "message": f"Could not control Calculator app: {str(e)}. Safe evaluation result: {expected_result}"
            }


if __name__ == "__main__":
    print("Testing CalculatorAutomation.calculate('Add 2+2', ensure_open=True)...")
    res = CalculatorAutomation.calculate("Add 2+2", ensure_open=True)
    print("Result:", res)

    print("\nTesting CalculatorAutomation.calculate('What is 15 times 6?', ensure_open=True)...")
    res2 = CalculatorAutomation.calculate("What is 15 times 6?", ensure_open=True)
    print("Result:", res2)
