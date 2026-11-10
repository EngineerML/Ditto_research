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

from .retrieval import SENTENCE_BREAK_RE, SENTENCE_START, STOPWORDS, UserIndex

SAID_LINE = " What those records say under {other}, newest first: {sentences}."
MAX_SAID = 6
MAX_SAID_CHARS = 220
# A lead-in such as "Shared calendar note:" or 'Forwarding a text I got: "' before the sentence itself.
LEAD_IN = re.compile(r"^(?:[A-Z][^:.!?]{0,60}:\s*[\"“]?)+")


def said_under(index: UserIndex, pids: list[str], word: str, labels: dict[str, str]) -> str:
    """The sentences of the user's own text that use the name, newest first, each once, with its record's mark.

    A fact told in passing inside a longer message ("... and the bus was cancelled. And Laz loves Ivory Quarry now.")
    is quoted on its own, so the deciding call reads it next to the tie that makes it count. Newest first, because a
    later record changes what an earlier one said; a sentence repeated under another lead-in counts once."""
    pattern = re.compile(r"(?<!\w)" + re.escape(word) + r"(?!\w)")
    nodes = sorted((index.nodes[pid] for pid in pids if pid in index.nodes), key=lambda node: (node.pair.timestamp, node.pair.pair_id), reverse=True)
    seen: set[str] = set()
    out: list[str] = []
    for node in nodes:
        parts: list[str] = []
        for part in SENTENCE_BREAK_RE.split(node.pair.prompt):
            # "Update on Laz:" introduces what follows; keep the two together.
            if parts and parts[-1].rstrip().endswith(":"):
                parts[-1] = parts[-1].rstrip() + " " + part
            else:
                parts.append(part)
        for sentence in parts:
            sentence = " ".join(sentence.split())
            key = LEAD_IN.sub("", sentence).strip(" \"“”").lower()
            if not sentence or not pattern.search(sentence) or key in seen or len(sentence) > MAX_SAID_CHARS:
                continue
            seen.add(key)
            mark = labels.get(node.pair.pair_id, f"pair {node.pair.pair_id}")
            out.append(f"{mark}: “{sentence}”")
    return "; ".join(out[:MAX_SAID])

WORD_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
SURNAME_AFTER = r"\b{name}\s+([A-Z][a-z]{{2,}})\b"
FIRST_BEFORE = r"\b([A-Z][a-z]{{1,}})\s+{surname}\b"
CALLED_CUES = (
    r"\bcall(?:s|ed)?\s+(?:(?:them|him|her)\s+)?([A-Z][a-z]{1,})\b",
    r"\bbeen\s+([A-Z][a-z]{1,})\s+to\s+everyone\b",
    r"\bgo(?:es)?\s+by\s+([A-Z][a-z]{1,})\b",
    r"\bknown\s+as\s+([A-Z][a-z]{1,})\b",
    r"\bnicknamed?\s+([A-Z][a-z]{1,})\b",
)
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
    out = []
    for link in links.values():
        link.records = holders(store, link.other, without=link.name)[:MAX_OTHER_RECORDS]
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


def chain_note(links: list[Link], labels: dict[str, str], index: UserIndex | None = None) -> str:
    lines = []
    for link in links:
        ties = []
        for kind, surname, name_pids, other_pids in link.ties:
            if kind == "surname":
                ties.append(SURNAME_TIE.format(where_name=mark_list(name_pids, labels), name=link.name, surname=surname, where_other=mark_list(other_pids, labels), other=link.other))
            else:
                ties.append(CALLED_TIE.format(where=mark_list(name_pids, labels), name=link.name, other=link.other))
        line = CHAIN_LINE.format(ties="; ".join(ties), other=link.other, name=link.name, marks=mark_list(link.records, labels))
        said = said_under(index, link.records, link.other, labels) if index is not None else ""
        lines.append(line + (SAID_LINE.format(other=link.other, sentences=said) if said else ""))
    return "\n".join(lines)
