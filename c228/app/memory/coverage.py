from __future__ import annotations

import re

from ..protocol import handed_out
from .people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS
from .retrieval import SENTENCE_START, STOPWORDS, UserIndex, tokens

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
SURNAME_HEADER = "Surnames the stored conversations write beside a one-word name the message uses, and the conversations holding each surname, found by the same mechanical word search and not checked:"
SURNAME_LINE = '"{name}" - {given} writes the name "{full}"; "{surname}" - {found}{others}'
SURNAME_OTHERS = ", where the names {names} are also written (a one-word name there may be anyone's); {held}"
SURNAME_HELD = '"{first}" - {found}'
MAX_SURNAME_LINES = 4
MAX_SURNAME_FULLS = 2
MAX_SURNAME_HOLDERS = 12
MAX_CHAIN_PINS = 6
MAX_CHAIN_WORDS = 3
CALLED_HEADER = "Names the stored conversations say a person the message names in full is called, found by the same mechanical word search and not checked:"
CALLED_LINE = '"{full}" - {given} says they are called "{alias}"; "{alias}" - {found}'
CALLED_RE = re.compile(r"\b(?:calls?|called|known as|goes by|go by|nicknamed?|answers to)\s+(?:them|him|her|it)?\s*([A-Z][a-z]+)\b|\bbeen\s+([A-Z][a-z]+)\s+to\s+everyone\b")
GIVEN_NAME_CUE_RE = re.compile(r"\b(?:goes by|go by|going by|known (?:to [a-z ]+ )?as|knows? (?:[A-Za-z]+ ){0,3}as|nicknamed?|nick|dubbed|a\.?k\.?a\.?|calls?|called|short for|answers to|first name|full name|real name|gone by|they mean|we mean|to (?:everyone|friends|family|us|the team|colleagues))\b|\([A-Z][a-z]+\)", re.IGNORECASE)
CAPITAL_WORD_RE = re.compile(r"\b[A-Z][a-z]{1,20}\b")
MAX_CALLED_LINES = 4
TITLE_WORDS = frozenset("Mr Mrs Ms Mx Miss Dr Prof Professor Sir Dame Lord Lady Aunt Auntie Uncle Grandma Grandpa Granny Nan Nana Coach Captain Doctor Nurse Officer Father Mother Mum Mom Dad Cousin Brother Sister".split())
MAX_CALLED_PINS = 10
ASKED_NAME_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")
NOT_NAMES = {"Which", "What", "When", "Where", "Who", "Whose", "Whom", "How", "Why", "Does", "Did", "Do", "Is", "Are", "Was", "Were", "The", "And", "Or", "But", "There", "Both", "Give", "Tell", "Remind", "Please", "Some", "Any", "All", "That", "This", "These", "Those", "Can", "Could", "Would", "Should", "Will", "Have", "Has", "Had", "Not", "Also", "Just", "Still", "Then", "Than", "From", "With", "Without", "About", "After", "Before", "Since", "Until", "For", "Into", "Over", "Under", "Only", "Even", "Ever", "Never", "Yes", "Okay", "Hey", "Hi", "Thanks", "Thank", "Sorry", "Right", "Well", "Now", "Today", "Tomorrow", "Yesterday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December", "You", "Your", "Yours", "Ditto"}


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


def asked_names(question: str) -> list[str]:
    out: list[str] = []
    in_full = {part for full in FULL_NAME_RE.findall(question) for part in full.split()}
    for match in ASKED_NAME_RE.finditer(question):
        word = match.group(1)
        if word in NOT_NAMES or word in out or word in in_full or starts_a_sentence(question, match.start()):
            continue
        out.append(word)
    return out


def short_prompt(index: UserIndex, pid: str) -> str:
    text = index.nodes[pid].pair.prompt
    return text if len(text) < SHORT_RECORD_CHARS else ""


def surname_chain(index: UserIndex, question: str) -> list[tuple[str, str, set[str], str, set[str], list[str]]]:
    """For each one-word name the message uses: the full names short stored conversations write for it, the conversations holding each surname, and other full names written beside that surname there."""
    out: list[tuple[str, str, set[str], str, set[str], list[str]]] = []
    for name in asked_names(question):
        fulls: dict[str, set[str]] = {}
        for pid in index.nodes:
            text = short_prompt(index, pid)
            for full in FULL_NAME_RE.findall(text) if text else ():
                if full.split()[0] == name and not mention(question, full):
                    fulls.setdefault(full, set()).add(pid)
        if not fulls or len(fulls) > MAX_SURNAME_FULLS:
            continue
        for full, where in sorted(fulls.items()):
            surname = full.split()[1]
            holders = name_holders(index, surname)
            if len(holders) > MAX_SURNAME_HOLDERS:
                continue
            others: list[str] = []
            for pid in sorted(holders):
                for other in FULL_NAME_RE.findall(short_prompt(index, pid)):
                    if other.split()[1] == surname and other != full and other not in others:
                        others.append(other)
            for pid in sorted(holders):
                text = short_prompt(index, pid)
                for match in ASKED_NAME_RE.finditer(text):
                    word = match.group(1)
                    if word in (surname, name) or word in NOT_NAMES or starts_a_sentence(text, match.start()) or any(word == other.split()[0] for other in others):
                        continue
                    if sum(1 for other in others if " " not in other) < MAX_CHAIN_WORDS:
                        others.append(word)
            out.append((name, full, where, surname, holders, others))
    return out[:MAX_SURNAME_LINES]


def cued_given_names(index: UserIndex, text: str, parts: set[str]) -> list[str]:
    """The one other capitalised word of a short record that says, with any of the cue words, what a person is called, when the store never writes that word in lower case and more than one stored conversation writes it capitalised: a name, not a sentence opener or an ordinary word. A record with two such words names nobody."""
    if not GIVEN_NAME_CUE_RE.search(text):
        return []
    words = [word for word in dict.fromkeys(CAPITAL_WORD_RE.findall(text)) if word not in parts and word not in NOT_NAMES and word not in SENTENCE_START and word.lower() not in STOPWORDS and index.lower_df[word.lower()] == 0 and index.cap_df[word.lower()] > 1]
    return words if len(words) == 1 else []


def called_names(index: UserIndex, question: str) -> list[tuple[str, str, set[str], set[str]]]:
    """For each full name the message writes, and each one-word name it uses: a name a short stored conversation holding that name says the person is called (for a one-word name, by the called-name phrases alone), where it says so, and the conversations holding that name."""
    out: list[tuple[str, str, set[str], set[str]]] = []
    fulls = list(dict.fromkeys(FULL_NAME_RE.findall(question)))
    for full in fulls + asked_names(question):
        one_word = " " not in full
        parts = set(full.split())
        where: dict[str, set[str]] = {}
        for pid in index.nodes:
            text = short_prompt(index, pid)
            if not text or not mention(text, full):
                continue
            for match in CALLED_RE.finditer(text):
                alias = match.group(1) or match.group(2)
                if alias and alias not in parts and alias not in NOT_NAMES:
                    where.setdefault(alias, set()).add(pid)
            if one_word:
                continue
            for alias in cued_given_names(index, text, parts):
                where.setdefault(alias, set()).add(pid)
        if one_word:
            for alias, pids in surname_hop_names(index, full, question).items():
                where.setdefault(alias, set()).update(pids)
        for alias, pids in sorted(where.items()):
            holders = {pid for pid in name_holders(index, alias) if short_prompt(index, pid)}
            if len(holders) > MAX_SURNAME_HOLDERS:
                continue
            out.append((full, alias, pids, holders))
    return out[:MAX_CALLED_LINES]


def surname_hop_names(index: UserIndex, name: str, question: str) -> dict[str, set[str]]:
    """Called names reached over a surname (M48): for each full name the store writes for a one-word name the message uses, the short conversations that hold its surname, not that full name, and a called-name cue give a called name: the name a called-name phrase gives, or the first word of another full name with that surname written there."""
    found: dict[str, set[str]] = {}
    for asked, full, where, surname, holders, others in surname_chain(index, question):
        if asked != name:
            continue
        for pid in holders:
            text = short_prompt(index, pid)
            if not text or mention(text, full) or not (CALLED_RE.search(text) or GIVEN_NAME_CUE_RE.search(text)):
                continue
            for match in CALLED_RE.finditer(text):
                alias = match.group(1) or match.group(2)
                if alias and alias not in (name, surname) and alias not in NOT_NAMES:
                    found.setdefault(alias, set()).add(pid)
            for match in re.finditer(r"\b([A-Z][a-z]+)\s+" + re.escape(surname) + r"\b", text):
                first = match.group(1)
                if first != name and first not in NOT_NAMES and first not in SENTENCE_START and first not in TITLE_WORDS:
                    found.setdefault(first, set()).add(pid)
    return found


def alias_ties(index: UserIndex, question: str) -> dict[str, tuple[str, list[str]]]:
    """For each name the called-name search (M48) finds for a name the message writes: that name and the stored conversations that state the tie, by pair id in date order. A name found for two names is left out."""
    ties: dict[str, tuple[str, list[str]]] = {}
    shared: set[str] = set()
    for full, alias, where, holders in called_names(index, question):
        if alias in ties and ties[alias][0] != full:
            shared.add(alias)
            continue
        ties[alias] = (full, sorted(where, key=lambda pid: (index.nodes[pid].pair.timestamp, pid)))
    return {alias: tie for alias, tie in ties.items() if alias not in shared}


def called_pins(index: UserIndex, question: str) -> list[str]:
    pins: list[str] = []
    for full, alias, where, holders in called_names(index, question):
        for pid in sorted(holders, key=lambda p: (index.nodes[p].pair.timestamp, p))[:MAX_CALLED_PINS]:
            if pid not in pins:
                pins.append(pid)
    return pins


def called_lines(index: UserIndex, question: str, labels: dict[str, str]) -> list[str]:
    return [CALLED_LINE.format(full=full, given=named(index, where, labels), alias=alias, found=named(index, holders, labels)) for full, alias, where, holders in called_names(index, question)]


def surname_pins(index: UserIndex, question: str) -> list[str]:
    pins: list[str] = []
    for pid in called_pins(index, question):
        if pid not in pins:
            pins.append(pid)
    for name, full, where, surname, holders, others in surname_chain(index, question):
        for pid in sorted(holders, key=lambda p: (index.nodes[p].pair.timestamp, p))[:MAX_CHAIN_PINS]:
            if pid not in pins:
                pins.append(pid)
        for other in others:
            first = other.split()[0]
            held = {pid for pid in name_holders(index, first) if short_prompt(index, pid)}
            if len(held) > MAX_SURNAME_HOLDERS:
                continue
            for pid in sorted(held, key=lambda p: (index.nodes[p].pair.timestamp, p))[:MAX_CHAIN_PINS]:
                if pid not in pins:
                    pins.append(pid)
    return pins


def surname_lines(index: UserIndex, question: str, labels: dict[str, str]) -> list[str]:
    lines = []
    for name, full, where, surname, holders, others in surname_chain(index, question):
        held = "; ".join(SURNAME_HELD.format(first=other.split()[0], found=named(index, {pid for pid in name_holders(index, other.split()[0]) if short_prompt(index, pid)}, labels)) for other in others)
        tail = SURNAME_OTHERS.format(names=", ".join(f'"{other}"' for other in others), held=held) if others else ""
        lines.append(SURNAME_LINE.format(name=name, given=named(index, where, labels), full=full, surname=surname, found=named(index, holders, labels), others=tail))
    return lines


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
    called = called_lines(index, question, labels)
    if called:
        lines += [CALLED_HEADER] + called
    chained = surname_lines(index, question, labels)
    if chained:
        lines += [SURNAME_HEADER] + chained
    return "\n".join(lines)
