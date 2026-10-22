from __future__ import annotations

import re

# Only markdown bold around the whole value is wrapper cleanup; a single asterisk or a backtick may be part of the
# value (a glob, a code span) and stays as the model wrote it.
WRAPPERS = ("**",)
# gpt-oss writes U+2011 (non-breaking hyphen) and U+2010 where a record has "-", and the v13 grader's text fold does
# not map them, so "ZAPELI‑6364" would not match "ZAPELI-6364". Only these two code points change, to the record's
# own character; letters, digits and every other character stay as the model wrote them.
PLAIN_HYPHENS = str.maketrans({"‐": "-", "‑": "-"})


def plain_hyphens(text: str | None) -> str | None:
    return text.translate(PLAIN_HYPHENS) if text else text
ANSWER_RE = re.compile(r"^\s*(?:ANSWER\s*:|(\*{1,2}|_{1,2})ANSWER\s*(?:\1\s*:|:\s*\1))\s*(?P<value>.*?)\s*$", re.IGNORECASE)


def slot_match(line: str) -> re.Match[str] | None:
    stripped = line.strip()
    match = ANSWER_RE.match(stripped.strip("`") if stripped.startswith("`") else line)
    if match is None:
        # A whole line set in emphasis ("**ANSWER: 15 days**") is the same slot line.
        inner = unwrap(stripped)
        if inner != stripped:
            match = ANSWER_RE.match(inner)
    return match


def unwrap(value: str) -> str:
    # Removes only a matching bold pair around a non-empty value; a value made of wrapper characters is kept.
    value = value.strip()
    while True:
        for mark in WRAPPERS:
            if len(value) > 2 * len(mark) and value.startswith(mark) and value.endswith(mark) and value[len(mark):-len(mark)].strip():
                value = value[len(mark):-len(mark)].strip()
                break
        else:
            return value


def parse_slot(text: str) -> tuple[str, str | None]:
    answer: str | None = None
    for line in text.splitlines():
        match = slot_match(line)
        if match:
            answer = unwrap(match.group("value"))
    return text.strip(), answer
