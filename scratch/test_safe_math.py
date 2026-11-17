import ast
import operator
import re
import sys
from typing import Any, Dict, Optional, Union

# Safe AST operators
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
    """
    Safely evaluates arithmetic expressions without using unrestricted eval().
    Supports +, -, *, /, //, %, **, unary +/- and parentheses.
    """
    expr = expression.strip()
    if not expr:
        raise ValueError("Empty mathematical expression")

    # Replace x or X with * if used as multiplication
    expr = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1 * \2", expr)

    # Parse AST
    tree = ast.parse(expr, mode='eval')

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        elif hasattr(ast, "Num") and isinstance(node, ast.Num):  # Python < 3.8 compat
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
    # Return int if clean integer
    if isinstance(res, float) and res.is_integer():
        return int(res)
    return res


def parse_math_phrase(phrase: str) -> Optional[str]:
    """
    Translates spoken or typed natural language math phrases into clean arithmetic expressions.
    """
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

    # Replace "negative" / "minus" before a digit with "-"
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

if __name__ == "__main__":
    test_cases = [
        "2+2",
        "Add 2+2",
        "What is 15 times 6?",
        "subtract 8 from 20",
        "divide 24 by 3",
        "3.5 plus 2.5",
        "negative 5 plus 10",
        "(4 + 5) * 2",
        "-8 + 20",
        "100 / 4",
    ]
    for tc in test_cases:
        p = parse_math_phrase(tc)
        if p:
            val = safe_eval_math(p)
            print(f"'{tc}' -> '{p}' -> {val}")
        else:
            print(f"'{tc}' -> NOT PARSED")
