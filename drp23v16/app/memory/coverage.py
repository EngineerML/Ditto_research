from __future__ import annotations

import re

from ..protocol import handed_out
from .people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS
from .retrieval import SENTENCE_START, STOPWORDS, UserIndex, tokens, within_one_edit

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
# From dan0l v34 (released): who a one-word name in the message is, and the people the store does hold when the
# message names someone no stored conversation names. Both are word searches over the user's own records.
ALIAS_HEADER = "Full names the stored conversations give a person the message calls by a one-word name, found by the same mechanical word search and not checked:"
ALIAS_LINE = '"{alias}" - the name {given} gives {name}; "{name}" - {found}'
MAX_ALIAS_LINES = 6
CONTACT_RE = re.compile(r"\b(?:e-?mail|work address|mail address)\b", re.IGNORECASE)
CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b")
UNNAMED_LINE = "Picked out by code from a word search over every stored conversation, not checked: there is no stored conversation that names {names}."
SAME_FIRST_LINE = "Stored conversations do name {people}, with the same first name."
UNNAMED_REPLY = "If you have no record of {name}, say that you have no record of {name}, and name the people above, by name only, as the ones the stored conversations do hold."
NAMED_WITH_LINE = "The ones that name {term} name {people}."
CALLED = '{name}, called "{alias}"'
SPELLING_MIN_CHARS = 4
NAMED_WITH_MAX_RECORDS = 6
MAX_NAMED_PEOPLE = 4


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
    labels = labels or {}
    lines = [COVERAGE_HEADER] if terms else []
    for key, surface, holders in terms:
        line = TERM_LINE.format(term=surface, found=named(index, holders, labels))
        if not holders:
            line += word_parts(index, key[2:], labels)
        lines.append(line)
    others = alias_lines(index, question, labels)
    if others:
        lines += [ALIAS_HEADER] + others
    return "\n".join(lines)


def given_names(index: UserIndex) -> dict[tuple[str, str], set[str]]:
    """(full name, one-word name) pairs a short record gives, with the records that give them."""
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
    lines = [ALIAS_LINE.format(alias=alias, given=named(index, where, labels), name=name, found=named(index, name_holders(index, name), labels))
             for name, alias, where in unshared_names(index) if mention(question, alias) and not mention(question, name)]
    return lines[:MAX_ALIAS_LINES]


def capitalized_terms(question: str) -> list[str]:
    out: list[str] = []
    for match in CAPITALIZED_RE.finditer(question):
        words = match.group(0).split()
        while words and (words[0] in SENTENCE_START or words[0].lower() in STOPWORDS):
            words.pop(0)
        if words:
            out.append(" ".join(words))
    return list(dict.fromkeys(out))


def asked_names(question: str) -> list[str]:
    return [term for term in capitalized_terms(question) if " " in term]


def words_pattern(name: str) -> re.Pattern[str]:
    return re.compile(r"\b" + r"\s+".join(re.escape(word) for word in name.split()) + r"\b", re.IGNORECASE)


def stored_anywhere(index: UserIndex, name: str) -> bool:
    pattern = words_pattern(name)
    return any(pattern.search(node.pair.prompt) or pattern.search(node.pair.response) for node in index.nodes.values())


def stored_misspelt(index: UserIndex, name: str) -> bool:
    words = name.lower().split()
    if any(len(word) < SPELLING_MIN_CHARS for word in words):
        return False
    for key, holders in index.postings.items():
        stored = key[2:].split()
        if key.startswith("n:") and holders and len(stored) == len(words) and all(a == b or within_one_edit(a, b) for a, b in zip(words, stored)):
            return True
    return False


def unnamed_people(index: UserIndex, question: str) -> list[str]:
    """Full names a contact question asks about that no stored conversation names, even one edit off."""
    if not index.nodes or not CONTACT_RE.search(question):
        return []
    return [name for name in asked_names(question) if not stored_anywhere(index, name) and not stored_misspelt(index, name)]


def nicknames(index: UserIndex) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, alias in given_names(index):
        out.setdefault(name, alias)
    return out


def listing(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def called(name: str, aliases: dict[str, str]) -> str:
    return CALLED.format(name=name, alias=aliases[name]) if name in aliases else name


def same_first_name(aliases: dict[str, str], unnamed: list[str]) -> list[str]:
    asked = {name.lower() for name in unnamed}
    firsts = {name.split()[0] for name in unnamed}
    return [name for name in sorted(aliases) if name.split()[0] in firsts and name.lower() not in asked][:MAX_NAMED_PEOPLE]


def named_with(index: UserIndex, question: str, unnamed: list[str], aliases: dict[str, str]) -> list[tuple[str, list[str]]]:
    asked = {name.lower() for name in unnamed}
    short = sorted((node.pair for node in index.nodes.values() if len(node.pair.prompt) < SHORT_RECORD_CHARS), key=lambda pair: (pair.timestamp, pair.pair_id))
    out: list[tuple[str, list[str]]] = []
    for term in capitalized_terms(question):
        if any(term.lower() in name or name in term.lower() for name in asked):
            continue
        pattern = words_pattern(term)
        holders = [pair.prompt for pair in short if pattern.search(pair.prompt)]
        if not 0 < len(holders) <= NAMED_WITH_MAX_RECORDS:
            continue
        people: list[str] = []
        for prompt in holders:
            for name in FULL_NAME_RE.findall(prompt):
                if name in aliases and name.lower() not in asked and name not in people:
                    people.append(name)
        if people:
            out.append((term, people[:MAX_NAMED_PEOPLE]))
    return out


def unnamed_note(index: UserIndex, question: str) -> str:
    """For a person the message names in full and no stored conversation names: the people the store does hold with
    that first name, or named alongside the message's other names, by name only."""
    unnamed = unnamed_people(index, question)
    if not unnamed:
        return ""
    aliases = nicknames(index)
    lines = [UNNAMED_LINE.format(names=" or ".join(unnamed))]
    first = same_first_name(aliases, unnamed)
    if first:
        lines.append(SAME_FIRST_LINE.format(people=listing([called(name, aliases) for name in first])))
    lines += [NAMED_WITH_LINE.format(term=term, people=listing([called(name, aliases) for name in people])) for term, people in named_with(index, question, unnamed, aliases)]
    if len(lines) > 1:
        lines.append(UNNAMED_REPLY.format(name=unnamed[0]))
    return " ".join(lines)
