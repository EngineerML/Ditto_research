from __future__ import annotations

import re

HYPHEN = re.compile(r"(?<=[A-Za-z0-9])[‐‑]|[‐‑](?=[A-Za-z])")
EMPHASIS = re.compile(r"(?<![\w*])\*\*(?=[^\s*])([^\n]*?[^\s*])\*\*(?![\w*])")
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
FIGURE = re.compile(r"[$€£]?\d[\d,]*(?:\.\d+)?%?")


def plain_hyphens(text: str) -> str:
    return HYPHEN.sub("-", text)


def unbold(match: re.Match[str]) -> str:
    after = match.string[match.end():]
    if FIGURE.fullmatch(match.group(1)) and after[:1] in (".", ",") and after[1:].strip():
        return match.group(0)
    return match.group(1)


def plain_emphasis(text: str) -> str:
    parts: list[str] = []
    last = 0
    for code in CODE.finditer(text):
        parts.append(EMPHASIS.sub(unbold, text[last:code.start()]))
        parts.append(code.group(0))
        last = code.end()
    parts.append(EMPHASIS.sub(unbold, text[last:]))
    return "".join(parts)


def plain_type(text: str) -> str:
    return plain_emphasis(plain_hyphens(text))
