from __future__ import annotations

import re
from dataclasses import dataclass

LIST_RE = re.compile(r":\s*([^:;.]+(?:,[^:;.]+){3,})")
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")
SPELLING_HINT = "\n[A check of spelling alone, not of meaning: {pairs}. Which words of the message name an option, and which listed option the message means, is for the message to decide.]"
PAIR = "“{written}” is spelled closest to the listed {option}"
LONGER_ONE = ", and {longer} is also listed"
LONGER_MANY = ", and {longer} are also listed"
LETTERS_PER_EDIT = 3
MAX_EDITS = 3
MAX_PAIRS = 5
MAX_LONGER = 2


@dataclass(frozen=True)
class Near:
    share: float
    start: int
    size: int
    written: str
    option: str


def distance(written: str, listed: str) -> int:
    two_back: list[int] = []
    one_back = list(range(len(listed) + 1))
    for row_at, letter in enumerate(written, start=1):
        row = [row_at] + [0] * len(listed)
        for at, other in enumerate(listed, start=1):
            row[at] = min(one_back[at] + 1, row[at - 1] + 1, one_back[at - 1] + (letter != other))
            if row_at > 1 and at > 1 and letter == listed[at - 2] and written[row_at - 2] == other:
                row[at] = min(row[at], two_back[at - 2] + 1)
        two_back, one_back = one_back, row
    return one_back[-1]


def edit_bound(letters: int) -> int:
    return min(MAX_EDITS, max(1, letters // LETTERS_PER_EDIT))


def listed_options(result: str) -> list[str]:
    seen: dict[str, None] = {}
    for found in LIST_RE.finditer(result):
        for option in found.group(1).split(","):
            name = option.strip()
            if name:
                seen.setdefault(name, None)
    return list(seen)


def near_options(options: list[str], message: str) -> list[Near]:
    words = WORD_RE.findall(message.lower())
    exact = {" ".join(WORD_RE.findall(option.lower())) for option in options}
    found: list[Near] = []
    for option in options:
        parts = WORD_RE.findall(option.lower())
        if not parts:
            continue
        target = " ".join(parts)
        letters = sum(len(part) for part in parts)
        bound = edit_bound(letters)
        for start in range(len(words) - len(parts) + 1):
            written = " ".join(words[start:start + len(parts)])
            if written in exact or abs(len(written) - len(target)) > bound:
                continue
            gap = distance(written, target)
            if gap <= bound:
                found.append(Near(gap / letters, start, len(parts), written, option))
    taken: set[int] = set()
    chosen: list[Near] = []
    for near in sorted(found, key=lambda near: (-near.size, near.share, near.start)):
        span = set(range(near.start, near.start + near.size))
        if span & taken:
            continue
        taken |= span
        chosen.append(near)
        if len(chosen) == MAX_PAIRS:
            break
    return sorted(chosen, key=lambda near: near.start)


def pair_text(near: Near, options: list[str]) -> str:
    longer = [other for other in options if other.lower().startswith(near.option.lower() + " ")][:MAX_LONGER]
    text = PAIR.format(written=near.written, option=near.option)
    if not longer:
        return text
    return text + (LONGER_ONE if len(longer) == 1 else LONGER_MANY).format(longer=" and ".join(longer))


def spelling_hint(result: str, message: str) -> str:
    options = listed_options(result)
    nears = near_options(options, message)
    if not nears:
        return ""
    return SPELLING_HINT.format(pairs="; ".join(pair_text(near, options) for near in nears))
