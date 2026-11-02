from __future__ import annotations

import re

VALUE_WRAPPERS = " \t`*"
ANSWER_RE = re.compile(r"^\s*(?:ANSWER\s*:|(\*{1,2}|_{1,2})ANSWER\s*(?:\1\s*:|:\s*\1))\s*(?P<value>.*?)\s*$", re.IGNORECASE)


def slot_match(line: str) -> re.Match[str] | None:
    stripped = line.strip()
    return ANSWER_RE.match(stripped.strip("`") if stripped.startswith("`") else line)


def parse_slot(text: str) -> tuple[str, str | None]:
    answer: str | None = None
    for line in text.splitlines():
        match = slot_match(line)
        if match:
            value = match.group("value")
            # Edge wrappers (backticks, `*`) come off; a value made only of them stays as the model wrote it.
            answer = value.strip(VALUE_WRAPPERS) or value.strip()
    return text.strip(), answer
