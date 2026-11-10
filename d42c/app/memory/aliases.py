from __future__ import annotations

import re
import time

from ..action import Outcome, TokenTally
from ..llm import LLM, LLMError
from .chain import SAID_LINE, said_under
from .retrieval import UserIndex

ALIAS_BRIEF = """Before the message is answered, look only at who it asks about: {names}. List every other name the records above use for {who} - a nickname, a handle, a short form of the name, a title - but only one that a record itself ties to {who}. Write one per line and nothing else; if the records tie no other name to {who}, write the single word none. Do not answer the message."""
ALIAS_NOTE = "A separate pass, not checked, read the records as calling {name} also {aliases}. Records that use those names: {marks}. Where they speak of {name}, they count for the answer as well; the records decide."
ALIAS_MAX_TOKENS = 1500
ALIAS_MIN_SECONDS = 30.0
MAX_ALIASES = 4
MAX_ALIAS_CHARS = 40
LINE_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def word_pattern(word: str) -> re.Pattern[str]:
    bare = word.lstrip("@")
    return re.compile(r"(?<!\w)@?" + re.escape(bare) + r"(?!\w)", re.IGNORECASE)


def record_texts(index: UserIndex) -> dict[str, str]:
    return {pid: node.pair.prompt + "\n" + node.pair.response for pid, node in index.nodes.items()}


def proposed(content: str, name: str) -> list[str]:
    out: list[str] = []
    for line in content.splitlines():
        alias = LINE_MARK.sub("", line).strip().strip(".,;:\"'“”")
        if not alias or alias.lower() in {"none", name.lower()} or len(alias) > MAX_ALIAS_CHARS:
            continue
        if alias.lower() not in {seen.lower() for seen in out}:
            out.append(alias)
    return out


def tied(texts: dict[str, str], name: str, alias: str) -> bool:
    person, other = word_pattern(name), word_pattern(alias)
    return any(person.search(text) and other.search(text) for text in texts.values())


def alias_records(texts: dict[str, str], name: str, alias: str) -> list[str]:
    person, other = word_pattern(name), word_pattern(alias)
    return [pid for pid, text in texts.items() if other.search(text) and not person.search(text)]


async def alias_note(llm: LLM, tally: TokenTally, outcome: Outcome, system: str, composed: str, names: list[str], index: UserIndex, labels: dict[str, str], deadline: float, effort: str) -> str:
    texts = record_texts(index)
    names = [name for name in names if any(word_pattern(name).search(text) for text in texts.values())]
    if not names or deadline - time.monotonic() < ALIAS_MIN_SECONDS:
        return ""
    who = " and ".join(names)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": composed + "\n\n" + ALIAS_BRIEF.format(names=who, who=who)}]
    try:
        result = await llm.chat(messages, None, deadline=deadline, max_tokens=ALIAS_MAX_TOKENS, reasoning_effort=effort)
    except LLMError as exc:
        tally.add(exc.usage)
        outcome.events.append(f"alias pass failed: {exc}")
        return ""
    tally.add(result)
    outcome.model_calls += 1
    if result.finish_reason == "length" or result.tool_calls:
        outcome.events.append("alias pass: no usable list")
        return ""
    notes: list[str] = []
    for name in names:
        aliases = [alias for alias in proposed(result.content, name) if tied(texts, name, alias)][:MAX_ALIASES]
        marks = sorted({labels[pid] for alias in aliases for pid in alias_records(texts, name, alias) if pid in labels}, key=lambda mark: int(mark[1:]))
        if aliases and marks:
            note = ALIAS_NOTE.format(name=name, aliases=", ".join(aliases), marks=", ".join(marks))
            for alias in aliases:
                said = said_under(index, alias_records(texts, name, alias), alias, labels)
                if said:
                    note += SAID_LINE.format(other=alias, sentences=said)
            notes.append(note)
    outcome.events.append(f"alias pass: {len(notes)} note(s)")
    return "\n".join(notes)
