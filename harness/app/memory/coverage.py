from __future__ import annotations

import re

from app.protocol import handed_out
from app.memory.retrieval import UserIndex, tokens

COVERAGE_HEADER = "Stored conversations that contain each distinctive term of the message, found by searching the whole store and not only the records shown above. A conversation shown above is named by its mark, any other by its pair id. This is a mechanical word search: a conversation may say the same thing in other words, and one named here may be unrelated to the message."
TERM_LINE = '"{term}" - {found}'
NONE_FOUND = "none"
WORD_TAIL = " (as separate words: {parts})"
WORD_PART = "{word} - {found}"
LIST_CUT = "(list cut)"
SAVED_NOTE = "a note saved earlier, not shown above and without a pair id"
SAVED_NOTES = "{count} notes saved earlier, not shown above and without pair ids"
MAX_TERMS = 10
MAX_NAMED = 12
COVERAGE_KINDS = ("n", "e", "c", "q", "i", "k")
KIND_RANK = {kind: position for position, kind in enumerate(COVERAGE_KINDS)}
SENTENCE_HEAD = re.compile(r"(?:^|[.!?;:]\s+|\n)\s*$")


def starts_a_sentence(question: str, position: int) -> bool:
    return bool(SENTENCE_HEAD.search(question[:position]))


def locate(question: str, term: str) -> tuple[str, int] | None:
    match = re.search(re.escape(term), question, re.I)
    return (match.group(0), match.start()) if match else None


def coverage_terms(index: UserIndex, question: str) -> list[tuple[str, str, set[str]]]:
    found: list[tuple[str, str, set[str]]] = []
    for key, kind in index.extract_values(question).items():
        if kind not in KIND_RANK:
            continue
        term = key[2:]
        if len(term) < 3:
            continue
        placed = locate(question, term)
        if placed is None:
            continue
        surface, position = placed
        if starts_a_sentence(question, position):
            continue
        holders = set(index.postings.get(key, ()))
        if not holders and " " not in term:
            continue
        found.append((key, surface, holders))
    found.sort(key=lambda item: (KIND_RANK[item[0][0]], len(item[2]), item[0]))
    return found[:MAX_TERMS]


def named(index: UserIndex, holders: set[str], labels: dict[str, str]) -> str:
    unshown = sum(1 for pid in holders if pid not in labels and not handed_out(pid))
    holders = {pid for pid in holders if pid in labels or handed_out(pid)}
    if not holders and not unshown:
        return NONE_FOUND
    shown = sorted((pid for pid in holders if pid in labels), key=lambda pid: int(labels[pid][1:]))
    others = sorted((pid for pid in holders if pid not in labels), key=lambda pid: (index.nodes[pid].pair.timestamp, pid))
    names = [labels[pid] for pid in shown] + [f"pair_id={pid}" for pid in others] + ([SAVED_NOTE if unshown == 1 else SAVED_NOTES.format(count=unshown)] if unshown else [])
    if len(names) > MAX_NAMED:
        return ", ".join(names[:MAX_NAMED]) + " " + LIST_CUT
    return ", ".join(names)


def word_holders(index: UserIndex, word: str) -> set[str]:
    return {pid for pid, node in index.nodes.items() if word in node.words}


def word_parts(index: UserIndex, term: str, labels: dict[str, str]) -> str:
    words = [word for word in tokens(term) if len(word) > 1]
    if len(words) < 2:
        return ""
    return WORD_TAIL.format(parts="; ".join(WORD_PART.format(word=word, found=named(index, word_holders(index, word), labels)) for word in words))


def question_coverage(index: UserIndex, question: str, labels: dict[str, str] | None = None) -> str:
    if not index.nodes:
        return ""
    terms = coverage_terms(index, question)
    if not terms:
        return ""
    labels = labels or {}
    lines = [COVERAGE_HEADER]
    for key, surface, holders in terms:
        line = TERM_LINE.format(term=surface, found=named(index, holders, labels))
        if not holders:
            line += word_parts(index, key[2:], labels)
        lines.append(line)
    return "\n".join(lines)
