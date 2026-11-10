"""Other first names for a person the message names by one first name, found through the user's own records.

Two record shapes tie a second first name to the asked one:
- a shared surname: one record writes the asked name with a surname ("Alexander Dunmore") and another record
  writes a different first name with the same surname ("Sandy Dunmore");
- a naming sentence: a record that holds the asked name says what people call them ("calls them Teddy").
The host only finds the records and names them; the note says the records decide whether the other name is
the same person, and the deciding model reads them and writes the answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .retrieval import SENTENCE_START, STOPWORDS, UserIndex

WORD_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
FULL_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
SURNAME_AFTER = r"\b{name}\s+([A-Z][a-z]{{2,}})\b"
FIRST_BEFORE = r"\b([A-Z][a-z]{{1,}})\s+{surname}\b"
CALLED_CUES = (
    r"\bcall(?:s|ed)?\s+(?:(?:them|him|her)\s+)?([A-Z][a-z]{1,})\b",
    r"\bbeen\s+([A-Z][a-z]{1,})\s+to\s+everyone\b",
    r"\bgo(?:es)?\s+by\s+([A-Z][a-z]{1,})\b",
    r"\bknown\s+as\s+([A-Z][a-z]{1,})\b",
    r"\bnicknamed?\s+([A-Z][a-z]{1,})\b",
)
# A sentence that says what someone is called: any of these words in a record that also holds the asked full name.
NAMING_RE = re.compile(r"\b(?:call(?:s|ed|ing)?|nick ?names?|nicknamed|go(?:es)? by|gone by|went by|known as|signs?|signed|answers? to|they mean|means|refer(?:s|red)? to)\b", re.IGNORECASE)
# The name a naming phrase points at: "calls them Teo", "says Waffles", "gone by Kipper", "as Yoyo", "known as Bix",
# or a quoted one-word name ("called “Joey”").
NAMED_AFTER = re.compile(r"(?:\b(?:call(?:s|ed|ing)?(?:\s+(?:them|him|her))?|says|say|by|as|nicknamed?|named)\s+[“\"']?([A-Z][a-z]{1,})\b|[“\"]([A-Z][a-z]{1,})[”\"])")
MAX_SURNAME_RECORDS = 4
MAX_OTHER_NAMES = 2
MAX_OTHER_RECORDS = 6
MAX_PINS = 12
CHAIN_LINE = "Picked out by code from a word search over every stored conversation, not checked: {ties}. Records that use {other} without {name}: {marks}. Where the records show that {other} is {name}, what they say about {other} counts for {name} as well, and a list asked about {name} takes its items from records under either name; a name that only looks like {name}'s, with no record tying it to {name}, is someone else. The records decide."
SURNAME_TIE = "{where_name} writes {name} {surname} and {where_other} writes {other} with {surname}"
CALLED_TIE = "{where} holds {name} together with the name {other}"


@dataclass
class Link:
    name: str
    other: str
    ties: list[tuple[str, str, list[str], list[str]]] = field(default_factory=list)  # (kind, surname, name pids, other pids)
    records: list[str] = field(default_factory=list)


def texts(index: UserIndex) -> dict[str, str]:
    return {pid: node.pair.prompt for pid, node in index.nodes.items()}


def plain(word: str) -> bool:
    return word not in SENTENCE_START and word.lower() not in STOPWORDS


def asked_first_names(message: str) -> list[str]:
    """One-word capitalized names in the message that no other capitalized word follows (no surname given)."""
    out: list[str] = []
    for match in WORD_RE.finditer(message):
        word = match.group(0)
        after = message[match.end():match.end() + 40]
        if not plain(word) or re.match(r"\s+[A-Z][a-z]", after) or (match.start() and re.search(r"[A-Z][a-z]+\s+$", message[:match.start()])):
            continue
        out.append(word)
    return list(dict.fromkeys(out))


def asked_full_names(message: str) -> list[str]:
    """Names of two or three capitalized words in the message ("Kenya Swartz")."""
    out: list[str] = []
    for match in FULL_RE.finditer(message):
        words = match.group(0).split()
        while words and not plain(words[0]):
            words.pop(0)
        if 2 <= len(words) <= 3 and all(plain(word) for word in words):
            out.append(" ".join(words))
    return list(dict.fromkeys(out))


def newest_distinct(index: UserIndex, pids: list[str]) -> list[str]:
    """The records newest first, a record whose text repeats an earlier-kept one left out."""
    nodes = sorted((index.nodes[pid] for pid in pids), key=lambda node: (node.pair.timestamp, node.pair.pair_id), reverse=True)
    kept: dict[str, str] = {}
    for node in nodes:
        kept.setdefault(" ".join(node.pair.prompt.split()), node.pair.pair_id)
    return list(kept.values())


def holders(store: dict[str, str], word: str, without: str = "") -> list[str]:
    pattern = re.compile(r"\b" + re.escape(word) + r"\b")
    skip = re.compile(r"\b" + re.escape(without) + r"\b") if without else None
    return [pid for pid, text in store.items() if pattern.search(text) and not (skip and skip.search(text))]


def stands_alone(store: dict[str, str], word: str) -> bool:
    """A person's first name: some record has it on its own before a lowercase word ("Sandy had ...").

    Company and place names ("Oricon Press", "Talgo Row") rarely stand alone, so they do not start a chain."""
    pattern = re.compile(r"\b" + re.escape(word) + r"\s+[a-z]")
    return any(pattern.search(text) for text in store.values())


def name_links(index: UserIndex, message: str) -> list[Link]:
    if not index.nodes:
        return []
    store = texts(index)
    links: dict[tuple[str, str], Link] = {}
    for name in asked_first_names(message):
        if not holders(store, name) or not stands_alone(store, name):
            continue
        surnames: dict[str, list[str]] = {}
        after = re.compile(SURNAME_AFTER.format(name=re.escape(name)))
        for pid, text in store.items():
            for surname in after.findall(text):
                if plain(surname) and surname != name:
                    surnames.setdefault(surname, []).append(pid)
        for surname, name_pids in surnames.items():
            if len(holders(store, surname)) > MAX_SURNAME_RECORDS:
                continue
            before = re.compile(FIRST_BEFORE.format(surname=re.escape(surname)))
            others: dict[str, list[str]] = {}
            for pid in holders(store, surname):
                if pid in name_pids:
                    continue
                # "Sandy Dunmore", or a naming sentence in a record about the surname ("the Strachan household ... calls Delia").
                found = before.findall(store[pid]) + [other for cue in CALLED_CUES for other in re.findall(cue, store[pid])]
                for other in found:
                    if other not in (name, surname) and plain(other):
                        others.setdefault(other, []).append(pid)
            if not others or len(others) > MAX_OTHER_NAMES:
                continue
            for other, other_pids in others.items():
                link = links.setdefault((name, other), Link(name, other))
                link.ties.append(("surname", surname, name_pids, other_pids))
        for pid in holders(store, name):
            for cue in CALLED_CUES:
                for other in re.findall(cue, store[pid]):
                    if other != name and plain(other):
                        link = links.setdefault((name, other), Link(name, other))
                        link.ties.append(("called", "", [pid], []))
    # A full name asked about ("Kenya Swartz"): a record that holds it and says what people call them ("everyone
    # there calls them Teo") ties the other name to it in one record.
    for full in asked_full_names(message):
        words = set(full.split())
        named: dict[str, list[str]] = {}
        for pid in holders(store, full):
            text = store[pid]
            if not NAMING_RE.search(text):
                continue
            for match in NAMED_AFTER.finditer(text):
                other = match.group(1) or match.group(2)
                if other not in words and plain(other):
                    named.setdefault(other, []).append(pid)
        # A person goes by one or two other names; more than that is a company or a place, not a nickname.
        if len(named) > MAX_OTHER_NAMES:
            continue
        for other, pids in named.items():
            link = links.setdefault((full, other), Link(full, other))
            link.ties.append(("called", "", pids, []))
    out = []
    for link in links.values():
        link.records = newest_distinct(index, holders(store, link.other, without=link.name))[:MAX_OTHER_RECORDS]
        if link.records and stands_alone(store, link.other):
            out.append(link)
    return out


def chain_pins(links: list[Link]) -> list[str]:
    pins: list[str] = []
    for link in links:
        for _, _, name_pids, other_pids in link.ties:
            pins += name_pids + other_pids
        pins += link.records
    return list(dict.fromkeys(pins))[:MAX_PINS]


def mark_list(pids: list[str], labels: dict[str, str]) -> str:
    return ", ".join(labels.get(pid, f"pair {pid} (not shown above)") for pid in dict.fromkeys(pids))


def chain_note(links: list[Link], labels: dict[str, str]) -> str:
    lines = []
    for link in links:
        ties = []
        for kind, surname, name_pids, other_pids in link.ties:
            if kind == "surname":
                ties.append(SURNAME_TIE.format(where_name=mark_list(name_pids, labels), name=link.name, surname=surname, where_other=mark_list(other_pids, labels), other=link.other))
            else:
                ties.append(CALLED_TIE.format(where=mark_list(name_pids, labels), name=link.name, other=link.other))
        lines.append(CHAIN_LINE.format(ties="; ".join(ties), other=link.other, name=link.name, marks=mark_list(link.records, labels)))
    return "\n".join(lines)
