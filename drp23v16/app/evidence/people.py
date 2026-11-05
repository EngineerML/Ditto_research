from __future__ import annotations

import difflib
import re

from ..protocol import MemoryPair

SHORT_RECORD_CHARS = 400
FULL_NAME_RE = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
ORDINARY_OPENERS = frozenset("on in for at re the this that think back quick current work about regarding".split())
OWNER_ASK_RE = re.compile(r"\b(?:owner|owns|leads?|running|runs|in charge)\b", re.IGNORECASE)
OWNER_REACH_RE = re.compile(r"\b(?:email|address|reach|contact)\b", re.IGNORECASE)
QUOTED_WORK_RE = re.compile(r"[“\"]([^”\"]{3,60})[”\"]")
OWNER_NAMED_RE = re.compile(r"\bowner is ([A-Z][a-z]+ [A-Z][a-z]+)\b|\b([A-Z][a-z]+ [A-Z][a-z]+) (?:owns|runs|leads) it\b|\bsits with ([A-Z][a-z]+ [A-Z][a-z]+)\b")
EMPLOYER_RE = re.compile(r"\bat ([A-Z][\w'-]*(?: (?:&|[A-Z][\w'-]*))*)")
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


def aliases_for(names: list[str], pairs: list[MemoryPair]) -> dict[str, list[str]]:
    # The names the user's own short notes say a person goes by ("... called “Flash” by everyone"), keyed by that name.
    out: dict[str, list[str]] = {}
    for name in names:
        parts = set(name.split())
        for pair in pairs:
            if name in pair.prompt and len(pair.prompt) < SHORT_RECORD_CHARS:
                for alias in ALIAS_RE.findall(pair.prompt):
                    if alias not in parts and name not in out.setdefault(alias, []):
                        out[alias].append(name)
    return out


def known_aliases(pairs: list[MemoryPair]) -> dict[str, list[str]]:
    short = "\n".join(pair.prompt for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS)
    return aliases_for(full_names(short, pairs), pairs)


def alias_lines(text: str, pairs: list[MemoryPair]) -> list[str]:
    # Which person each name used in the text stands for, and which nicknames a full name in the text goes by.
    known = known_aliases(pairs)
    lines = [f"- “{alias}”: {' or '.join(names)}" for alias, names in sorted(known.items()) if re.search(r"\b" + re.escape(alias) + r"(?:'s)?\b", text)]
    for name in full_names(text, pairs):
        nicks = sorted(alias for alias, names in known.items() if names == [name])
        if nicks:
            lines.append(f"- {name}: called " + " or ".join(f"“{nick}”" for nick in nicks) + " in the notes")
    return lines


def nickname_cards(text: str, pairs: list[MemoryPair]) -> list[MemoryPair]:
    # The short notes of each person the text names in full who also goes by a nickname in their own notes, under either name.
    known = known_aliases(pairs)
    named = [name for name in full_names(text, pairs) if any(names == [name] for names in known.values())]
    return cards_for(named, pairs)


def namesakes(text: str, pairs: list[MemoryPair]) -> dict[str, list[str]]:
    # People the text names in full whom no short note names, each with the people of the notes (those who go by a
    # nickname there) who share their first or last name. A name a letter or two off a known one is that person misspelt.
    short = [pair.prompt for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS]
    people = list(dict.fromkeys(name for names in known_aliases(pairs).values() for name in names))
    out: dict[str, list[str]] = {}
    for asked in dict.fromkeys(FULL_NAME_RE.findall(text)):
        if any(asked in prompt for prompt in short):
            continue
        first, last = asked.split()
        alike = [name for name in people if name.split()[0] == first or name.split()[1] == last]
        if alike and not any(difflib.SequenceMatcher(None, asked, name).ratio() >= 0.85 for name in alike):
            out[asked] = alike
    return out


def people_at(text: str, pairs: list[MemoryPair]) -> list[str]:
    # When the text names in full someone no short note names, "at" an employer: the people of the notes at that employer.
    short = [pair.prompt for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS]
    asked = [name for name in dict.fromkeys(FULL_NAME_RE.findall(text)) if not any(name in prompt for prompt in short)]
    places = EMPLOYER_RE.findall(text)
    if not asked or not places:
        return []
    people = dict.fromkeys(name for names in known_aliases(pairs).values() for name in names)
    return [name for name in people if any(name in prompt and place in prompt for prompt in short for place in places) and not any(difflib.SequenceMatcher(None, one, name).ratio() >= 0.85 for one in asked)]


def no_email_held(text: str, pairs: list[MemoryPair]) -> tuple[str, list[str], list[MemoryPair]] | None:
    # The person the text names first, the other people it points to (a nickname it uses, a namesake, someone at the employer it
    # names), and all those people's short notes. None when nobody else is there to name. Whether a note gives the person's email
    # is the model's to read.
    names = [name for name in dict.fromkeys(FULL_NAME_RE.findall(text)) if name.split()[0].lower() not in ORDINARY_OPENERS]
    if not names:
        return None
    asked = names[0]
    known = known_aliases(pairs)
    people = list(dict.fromkeys(name for alias, held in known.items() if re.search(r"\b" + re.escape(alias) + r"(?:'s)?\b", text) for name in held))
    people += [name for name in namesakes(text, pairs).get(asked, []) if name not in people]
    people += [name for name in people_at(text, pairs) if name not in people]
    people = [name for name in people if name != asked]
    if not people or any(difflib.SequenceMatcher(None, asked, name).ratio() >= 0.85 for names_held in known.values() for name in names_held):
        return None
    return asked, people, by_date(cards_for([asked, *people], pairs))


def owner_names(text: str, pairs: list[MemoryPair]) -> list[str]:
    # The person a note names as the owner of the work the text puts in quotes, when the text asks how to reach them.
    if not (OWNER_ASK_RE.search(text) and OWNER_REACH_RE.search(text)):
        return []
    quoted = [found.lower() for found in QUOTED_WORK_RE.findall(text)]
    held = [next(name for name in found.groups() if name) for pair in pairs if any(work in pair.prompt.lower() for work in quoted) and (found := OWNER_NAMED_RE.search(pair.prompt))]
    return list(dict.fromkeys(held))
