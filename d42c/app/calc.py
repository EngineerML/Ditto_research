from __future__ import annotations

import ast
import json
import math
import operator
import re
import unicodedata
from typing import Any

BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
FUNCTIONS = {"min": min, "max": max, "abs": abs, "round": round, "sum": sum, "floor": math.floor, "ceil": math.ceil}
MAX_EXPRESSION_CHARS = 400
MAX_ABS_VALUE = 1e15
MAX_POWER_DIGITS = 308
MAX_ROUND_PLACES = 15
MAX_TERMS = 24
MAX_TERM_CHARS = 240
CURRENCY_PREFIX_LETTERS = 3
FIGURE_OPENERS = "0123456789.("
GROUPED_FIGURE_RE = re.compile(r"(?<![\d.])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)")
LIST_CALL_RE = re.compile(r"(?<![\w.])(?:sum|min|max)\s*$")
EVALUATION_ERRORS = (TypeError, ValueError, OverflowError, ZeroDivisionError, RecursionError)

CALCULATE_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Arithmetic over figures you take from the attached records: + - * / parentheses, min, max, sum, abs, round, and also floor, ceil, //, % and ** (^ is read as **). Inside the brackets of sum, min or max, a comma with no space after it between whole digit groups separates arguments, so sum(3,100) is 103, unless the group after it starts with 0, so sum(2,050) is 2050; anywhere else a comma inside a figure groups thousands. The receipt shows how the expression was read. Returns the result of the expression you supply, nothing more.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Numbers, operators and currency marks, for example (1200 - 350) * 2"},
                "terms": {"type": "array", "items": {"type": "string"}, "description": 'One entry per figure in the expression: the figure with its sign, then the record label and the words around it, for example "-350: M2, the words the record puts around it".'},
            },
            "required": ["expression", "terms"],
        },
    },
}
READING_LINE = "Read as: {reading}\n"
CALC_RECEIPT = "{expression} = {result}\n{reading}Terms as you listed them:\n{terms}\nThis receipt is arithmetic over what you supplied. Which figures belong and which sign each carries come from your reading of the records, and you may change either and calculate again."


class CalcError(ValueError):
    pass


def _ascii_letter(char: str) -> bool:
    return char.isascii() and char.isalpha()


def _currency_prefix_length(kept: list[str]) -> int:
    run = 0
    while run < CURRENCY_PREFIX_LETTERS and len(kept) > run and _ascii_letter(kept[-1 - run]):
        run += 1
    return 0 if run and len(kept) > run and _ascii_letter(kept[-1 - run]) else run


def without_currency_marks(text: str) -> str:
    kept: list[str] = []
    for index, char in enumerate(text):
        ahead = text[index + 1:].lstrip(" ")[:1] if unicodedata.category(char) == "Sc" else ""
        if not ahead or ahead not in FIGURE_OPENERS:
            kept.append(char)
            continue
        if ahead.isdigit() and (prefix := _currency_prefix_length(kept)):
            del kept[len(kept) - prefix:]
    return "".join(kept)


def enclosing_opener(text: str, start: int) -> int | None:
    depth = 0
    for index in range(start - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            if not depth:
                return index
            depth -= 1
    return None


def call_arguments(text: str, start: int) -> str | None:
    opener = enclosing_opener(text, start)
    if opener is None or not LIST_CALL_RE.search(text[:opener]):
        return None
    depth = 0
    for index in range(opener + 1, len(text)):
        depth += (text[index] == "(") - (text[index] == ")")
        if depth < 0:
            return text[opener + 1:index]
    return text[opener + 1:]


def spaced_separators(arguments: str) -> bool:
    depth = 0
    for index, char in enumerate(arguments):
        depth += (char == "(") - (char == ")")
        if char == "," and depth == 0 and arguments[index + 1:index + 2].isspace():
            return True
    return False


def marked_figure(text: str, start: int) -> bool:
    before = text[:start].rstrip(" ")[-1:]
    return bool(before) and unicodedata.category(before) == "Sc"


def figure_lists_arguments(text: str, match: re.Match[str]) -> bool:
    figure = match.group(0)
    if "." in figure or marked_figure(text, match.start()) or any(group.startswith("0") for group in figure.split(",")[1:]):
        return False
    arguments = call_arguments(text, match.start())
    return arguments is not None and not spaced_separators(arguments)


def read_commas(expression: str) -> tuple[str, bool]:
    split: list[str] = []

    def fold(match: re.Match[str]) -> str:
        if figure_lists_arguments(expression, match):
            split.append(match.group(0))
            return match.group(0).replace(",", ", ")
        return match.group(0).replace(",", "")

    return GROUPED_FIGURE_RE.sub(fold, expression), bool(split)


def power_digits(base: float, exponent: float) -> float:
    magnitude = abs(base)
    return exponent * math.log10(magnitude) if magnitude > 1 else 0.0


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 16:
            raise CalcError("exponent too large")
        if isinstance(node.op, ast.Pow) and power_digits(left, right) > MAX_POWER_DIGITS:
            raise CalcError("result is too large")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise CalcError("division by zero")
        return BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords:
        args = [_evaluate(arg) for arg in node.args]
        if node.func.id == "sum":
            return FUNCTIONS["sum"](args)
        if node.func.id == "round" and len(args) > 1 and abs(args[1]) > MAX_ROUND_PLACES:
            raise CalcError("rounding places out of range")
        return FUNCTIONS[node.func.id](*args)
    if isinstance(node, (ast.List, ast.Tuple)):
        raise CalcError("lists are not supported; pass numbers directly")
    raise CalcError(f"unsupported expression element: {type(node).__name__}")


def evaluate(expression: str) -> float:
    if len(expression.strip()) > MAX_EXPRESSION_CHARS:
        raise CalcError("expression is empty or too long")
    reading, _ = read_commas(expression)
    text = without_currency_marks(reading).replace("×", "*").replace("−", "-").replace("^", "**").strip()
    if not text:
        raise CalcError("expression is empty or too long")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise CalcError(f"cannot parse expression: {exc.msg}") from exc
    try:
        value = _evaluate(tree)
    except CalcError:
        raise
    except EVALUATION_ERRORS as exc:
        raise CalcError(f"cannot evaluate expression: {exc}") from exc
    if isinstance(value, complex):
        raise CalcError("result is not a real number")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise CalcError("result is not a finite number")
    if abs(value) > MAX_ABS_VALUE:
        raise CalcError("result is too large")
    return value


def format_result(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{round(value, 6):.6f}".rstrip("0").rstrip(".")


def listed_terms(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(term).strip()[:MAX_TERM_CHARS] for term in raw[:MAX_TERMS] if str(term).strip()]


def run_calculate(args: dict[str, Any]) -> str:
    expression = str(args.get("expression") or args.get("expr") or "").strip()
    reading, split = read_commas(expression) if len(expression) <= MAX_EXPRESSION_CHARS else (expression, False)
    try:
        value = evaluate(expression)
    except CalcError as exc:
        return json.dumps({"error": str(exc), "read_as": reading} if split else {"error": str(exc)})
    terms = listed_terms(args.get("terms"))
    return CALC_RECEIPT.format(expression=expression, result=format_result(value), reading=READING_LINE.format(reading=reading) if split else "", terms="\n".join(terms) if terms else "(none listed)")
