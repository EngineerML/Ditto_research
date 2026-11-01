from __future__ import annotations

import re

from ..protocol import handed_out
from .people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS
from .retrieval import UserIndex, tokens

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
ALIAS_HEADER = "Full names the stored conversations give a person the message calls by a one-word name, found by the same mechanical word search and not checked:"
ALIAS_LINE = '"{alias}" - the name {given} gives {name}; "{name}" - {found}'
NAMED_HEADER = "One-word names the stored conversations give a person the message names in full, found by the same mechanical word search and not checked:"
NAMED_LINE = '"{name}" - {given} gives them the name "{alias}"; "{alias}" - {found}'
MAX_ALIAS_LINES = 6


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


def given_names(index: UserIndex) -> dict[tuple[str, str], set[str]]:
    given: dict[tuple[str, str], set[str]] = {}
    for pid, node in index.nodes.items():
        text = node.pair.prompt
        if len(text) >= SHORT_RECORD_CHARS:
            continue
        names = set(FULL_NAME_RE.findall(text))
        if len(names) != 1:
            continue
        name = next(iter(names))
        for alias in ALIAS_RE.findall(text):
            given.setdefault((name, alias), set()).add(pid)
    return given


def mention(text: str, word: str) -> bool:
    return bool(re.search(r"\b" + re.escape(word) + r"\b", text))


def name_holders(index: UserIndex, word: str) -> set[str]:
    pattern = re.compile(r"\b" + re.escape(word) + r"\b")
    return {pid for pid, node in index.nodes.items() if pattern.search(node.pair.prompt) or pattern.search(node.pair.response)}


def unshared_names(index: UserIndex) -> list[tuple[str, str, set[str]]]:
    given = given_names(index)
    owners: dict[str, set[str]] = {}
    for name, alias in given:
        owners.setdefault(alias, set()).add(name)
    return [(name, alias, where) for (name, alias), where in sorted(given.items()) if len(owners[alias]) == 1]


def alias_lines(index: UserIndex, question: str, labels: dict[str, str]) -> list[str]:
    lines = [ALIAS_LINE.format(alias=alias, given=named(index, where, labels), name=name, found=named(index, name_holders(index, name), labels)) for name, alias, where in unshared_names(index) if mention(question, alias) and not mention(question, name)]
    return lines[:MAX_ALIAS_LINES]


def named_lines(index: UserIndex, question: str, labels: dict[str, str]) -> list[str]:
    lines = [NAMED_LINE.format(name=name, given=named(index, where, labels), alias=alias, found=named(index, name_holders(index, alias), labels)) for name, alias, where in unshared_names(index) if mention(question, name) and not mention(question, alias)]
    return lines[:MAX_ALIAS_LINES]


def question_coverage(index: UserIndex, question: str, labels: dict[str, str] | None = None) -> str:
    if not index.nodes:
        return ""
    labels = labels or {}
    terms = coverage_terms(index, question)
    lines = [COVERAGE_HEADER] if terms else []
    for key, surface, holders in terms:
        line = TERM_LINE.format(term=surface, found=named(index, holders, labels))
        if not holders:
            line += word_parts(index, key[2:], labels)
        lines.append(line)
    others = alias_lines(index, question, labels)
    if others:
        lines += [ALIAS_HEADER] + others
    called = named_lines(index, question, labels)
    if called:
        lines += [NAMED_HEADER] + called
    return "\n".join(lines)
