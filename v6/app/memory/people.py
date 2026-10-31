from __future__ import annotations

import re

from ..protocol import MemoryPair

SHORT_RECORD_CHARS = 400
FULL_NAME_RE = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
ALIAS_RE = re.compile(r"[“\"]([A-Z][A-Za-z\-]{1,20})[.,]?[”\"]")


def by_date(records: list[MemoryPair]) -> list[MemoryPair]:
    return sorted(records, key=lambda pair: (pair.timestamp, pair.pair_id))


def full_names(text: str, pairs: list[MemoryPair]) -> list[str]:
    short = [pair.prompt for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS]
    return [name for name in dict.fromkeys(FULL_NAME_RE.findall(text)) if any(name in prompt for prompt in short)]


def person_card(name: str, pairs: list[MemoryPair]) -> list[MemoryPair]:
    first = [pair for pair in pairs if name in pair.prompt and len(pair.prompt) < SHORT_RECORD_CHARS]
    parts = set(name.split())
    aliases = {alias for pair in first for alias in ALIAS_RE.findall(pair.prompt) if alias not in parts}
    patterns = [re.compile(r"\b" + re.escape(alias) + r"\b") for alias in sorted(aliases)]
    held = {pair.pair_id for pair in first}
    second = [pair for pair in pairs if pair.pair_id not in held and len(pair.prompt) < SHORT_RECORD_CHARS and any(pattern.search(pair.prompt) for pattern in patterns)]
    return first + second


def cards_for(names: list[str], pairs: list[MemoryPair]) -> list[MemoryPair]:
    out: dict[str, MemoryPair] = {}
    for name in names:
        for pair in person_card(name, pairs):
            out.setdefault(pair.pair_id, pair)
    return by_date(list(out.values()))
