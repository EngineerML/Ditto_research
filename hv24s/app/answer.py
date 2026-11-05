from __future__ import annotations

import re

VALUE_WRAPPERS = " \t`"
BOLD_WRAP_RE = re.compile(r"^(\*{1,3})(?=\S)(.*\S)\1$")
ANSWER_RE = re.compile(r"^\s*(?:ANSWER\s*:|(\*{1,2}|_{1,2})ANSWER\s*(?:\1\s*:|:\s*\1))\s*(?P<value>.*?)\s*$", re.IGNORECASE)


def slot_match(line: str) -> re.Match[str] | None:
    stripped = line.strip()
    return ANSWER_RE.match(stripped.strip("`") if stripped.startswith("`") else line)


def parse_slot(text: str) -> tuple[str, str | None]:
    answer: str | None = None
    for line in text.splitlines():
        match = slot_match(line)
        if match:
            # Only wrapping marks come off: a value that is nothing but such a mark stays.
            value = match.group("value").strip(VALUE_WRAPPERS)
            wrapped = BOLD_WRAP_RE.match(value)
            answer = (wrapped.group(2) if wrapped else value) or match.group("value").strip()
    return text.strip(), answer
