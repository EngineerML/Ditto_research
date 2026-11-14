"""Short notes shown for a question on an invoice, a trip, a messaging handle or an email, labelled as found by code and not checked. The deciding model reads them and writes the reply; nothing is computed from them. Reused from the released Hades v26 source (`evidence_view`, `app/short.py`); `view_guide.py`, `memory/view_people.py`, `guide_spelling.py` and `english_words.py` are that source's `guide_records.py`, `memory/people.py`, `guide_spelling.py` and `english_words.py`, used only on this path."""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import guide_records as guide_rules
from . import view_guide as guide_records
from .action import Outcome, VALUE_VERBATIM
from .english_words import WORDS
from .guide_spelling import SHORT_WORDS, fold, read_form
from .memory import coverage
from .memory.coverage import alias_ties
from .memory.retrieval import QUOTE_RE, UserIndex
from .memory.view_people import FULL_NAME_RE, ORDINARY_OPENERS, by_date, no_email_held, person_card
from .protocol import MemoryPair, RunRequest
from .records import RecordsEngine
from .short import MESSAGE_HEADER, NOTES_TOGETHER, SHORT_OPENING, decide, short_system

MONTH_NUMBERS = {name: number for number, name in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1)}
ONE_LINE_ANSWER = "Reply with one line only, beginning 'ANSWER: ', with only the value asked for, as short as the notes put it, in their words; when several things are asked, give them on that line in the order asked, separated by ' ; '. Do all your working before you reply and write none of it: no figure or date the message did not ask for, not even those the answer was worked out from, and any money figure to its two decimal places."
NOT_STATED_LINE = "If the notes do not state something asked, say so on that line, with what they do hold on it."
ACCOUNT_NOTE_CHARS = 600
CONTACT_ASK_WORD_RE = re.compile(r"\b(?:e-?mail|address|inbox|contact)\b", re.IGNORECASE)
CONTACT_ASKS_RE = re.compile(r"\b(?:what|whats|which|who|remind)\b", re.IGNORECASE)
CONTACT_NOTE = "A later sentence replaces an earlier one. Give the address the latest of them gives for the party the message asks about."
CONTACT_SHOWN = "The sentences of the user's notes that name this project and give an address, each after the day it was filed; found by code; not checked:\n{notes}"
PARTY_WORD_RE = re.compile(r"\b[A-Z][a-z]{3,}\b")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
ASKED_DAY_RE = re.compile(r"\b(jan\w*|feb\w*|mar\w*|apr\w*|may|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*)\s+(\d{1,2}),?\s+(20\d\d)\b", re.IGNORECASE)
DATED_EMAIL_NOTE = "Read the day before each note above against the date the message asks about, and give the address your reading leaves on file then, with nothing about other dates, ending with the line 'ANSWER: <that email>'. If none was on file yet, say so."
EMAIL_HELD_LINE = "If a note above gives an email address for the person asked about, under any name they go by and even with a word in it misspelt, the ANSWER line is that address; only if none does, say you have no record."
FIGURE_MONEY_RE = re.compile(r"[$€£]\s?\d")
HANDLE_DROPPED_LINE = "If a note above asks to drop this handle, it is gone: the ANSWER line says you no longer have a handle for them on record and names the nickname, employer, role and city the notes give; a nickname is not a handle."
HANDLE_RETIRED_RE = re.compile(r"\b(?:retired|remove|removed|drop|dropped|closed that account|no longer use|stopped using|deleted)\b", re.IGNORECASE)
HANDLE_SHOWN = "The user's short notes on {asked}, found by code; not checked:\n{notes}"
HANDLE_WORD_RE = re.compile(r"\b(?:signal|whatsapp|telegram|handle)\b", re.IGNORECASE)
INVOICE_ASK_RE = re.compile(r"\b(?:invoice|bill|owe|owed|owing|balance|remains?|outstanding)\b", re.IGNORECASE)
INVOICE_HEADER = "The user's saved notes on the invoice this message names, found by code; not checked:"
INVOICE_RE = re.compile(r"\b(?:INV|AP)-[A-Z0-9]+\b")
NO_EMAIL_MAX_NOTES = 16
NO_EMAIL_NOTE = "An address asked for here is an email address. If one of these notes gives a work email for the person the message asks about, give it. Only if none does: tell the user you have no record of a work email for that person, and in the same reply who the notes do hold: each of the people code matched above, if the notes bear that out, by full name with their role, employer and city as the notes give them, as a different person where the name differs, and not the person asked about unless named there, with no email address of anyone, not even one of theirs, all on the one line: 'ANSWER: I have no record of a work email for <the person asked about>; the notes hold <full name>, <role> at <employer> in <city>'."
NO_EMAIL_SHOWN = "The user's short notes naming {asked}, and any nickname those notes give them, found by code; not checked. Code matched these names to the message and may be wrong: {people}. The notes:\n{notes}"
OWED_ASK_RE = re.compile(r"\b(?:owe|owed|owing|balance|remains?|outstanding|left)\b", re.IGNORECASE)
PAYABLES_HEADER = "The user's saved notes on this project's payables record, found by code from the project's name, each after the day it was filed; not checked:"
PAYABLES_NOTE = "The latest total in these notes is the total, whatever an earlier note gave. A payment stays as written unless a note changes it."
PAYABLES_RE = re.compile(r"\bAP-[A-Z0-9]+\b")
SAVED_EMAIL_ASK_RE = re.compile(r"\b(?:which|what)\b[^.?]{0,40}\b(?:email|address)\b[^.?]{0,40}\b(?:did i|do i)\b", re.IGNORECASE)
TRIP_CHAIN_CHARS = 450
TRIP_DATED_LINE = "Go by the notes shown above, as they stood on the date the message asks about."
TRIP_HEADER = "The user's saved notes on this trip, found by code from its name, oldest first, each after the day it was filed; not checked:"
TRIP_HEAD_RE = re.compile(r"\bOur ([a-z]+(?: [a-z]+){0,3}) was\b")
TRIP_PERSON_RE = re.compile(r"\b([A-Z][a-z]+) and I\b")
TRIP_PLACE_RE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
TRIP_READ_NOTE = "Read these notes with their dates and work out what they give before you reply, and give the one thing the message asks for."
TRIP_TOTAL_LINE = "Reply with the total alone: 'ANSWER: <total> days'."
VIEW_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {ONE_LINE_ANSWER} Write any date in full, with day, month and year. A thread that was finished, dropped or cancelled still has the last person who held it and the last next action a note gave. {NOT_STATED_LINE}"

@dataclass(frozen=True)
class EvidenceView:
    shown: str
    notes: list[str]
    max_tokens: int = 0
    closing: str = ""
    list_ask: bool = False  # a list of one person's things: what the notes do not hold goes unsaid


def names_a_person(text: str) -> bool:
    # Two capitalised words whose first is not an ordinary English word ("On Ace's", "Current Email"), or inside a sentence, where
    # capitals are not just the start of it, whose second is not: "Summer Bisson" is a person even though summer is a word.
    def plain(word: str) -> bool:
        return len(word) <= 2 or word in WORDS or word in SHORT_WORDS
    for found in FULL_NAME_RE.finditer(text):
        first, second = found.group(0).lower().split()[:2]
        inside = bool(text[:found.start()].strip()) and text[:found.start()].rstrip()[-1] not in ".?!:;"
        if not plain(first) or (inside and not plain(second)):
            return True
    return False


def no_email_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    read = read_form(message)
    # Asks for an address the user holds, naming a person: not a request to send something, not a thread's owner.
    if not (guide_records.asks_contact_detail(message) or SAVED_EMAIL_ASK_RE.search(read)) or guide_records.asks_handle(message) or guide_records.ASKED_DATE_RE.search(read) or not names_a_person(message):
        return None
    found = no_email_held(message, pairs)
    if found is None or not found[2]:
        return None
    asked, people, notes = found
    lines = "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in notes[:NO_EMAIL_MAX_NOTES])
    return EvidenceView(NO_EMAIL_SHOWN.format(asked=asked, people=", ".join(people), notes=lines), [NO_EMAIL_NOTE], closing=EMAIL_HELD_LINE)


def partial_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # What is still owed after a payment on the invoice the message names: the short notes on that invoice.
    read = read_form(message)
    codes = INVOICE_RE.findall(message)
    if not codes or not OWED_ASK_RE.search(read):
        return None
    held = [pair for pair in pairs if len(pair.prompt) < ACCOUNT_NOTE_CHARS and any(code in pair.prompt for code in codes)]
    if not held:
        return None
    return EvidenceView(f"{INVOICE_HEADER}\n" + "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in by_date(held)), [guide_records.PARTIAL_PAYMENT_NOTE, *(note for note in guide_records.record_notes(message) if note != guide_records.PARTIAL_PAYMENT_NOTE)])


def trip_chain(message: str, pairs: list[MemoryPair]) -> tuple[list[MemoryPair], set[str]]:
    # The note that names the trip the message names, and the notes on it: later notes do not repeat its name but speak of the
    # places it went through, with the person named in the first note.
    short = [pair for pair in pairs if len(pair.prompt) < TRIP_CHAIN_CHARS]
    low = f"{read_form(message).lower()} {message.lower()}"
    heads = [pair for pair in short if (name := TRIP_HEAD_RE.search(pair.prompt)) and re.search(r"\b" + re.escape(name.group(1)) + r"\b", low)]
    if len(heads) != 1:
        return [], set()
    head = heads[0]
    route = head.prompt.split("through", 1)[-1].split(" that ", 1)[0]
    places = set(TRIP_PLACE_RE.findall(route))
    named = [found.group(1) for pair in short if pair is not head and (found := TRIP_PERSON_RE.search(pair.prompt)) and sum(place in pair.prompt for place in places) >= 2]
    person = next((name for name in named if re.search(r"\b" + re.escape(name) + r"\b", head.prompt)), "")
    if not person:
        return [], set()
    rest = [pair for pair in short if pair is not head and re.search(r"\b" + re.escape(person) + r" and I\b", pair.prompt) and any(place in pair.prompt for place in places)]
    return by_date([head, *rest]), places


def asked_day(read: str) -> str:
    found = ASKED_DAY_RE.search(read)
    if not found:
        return ""
    month = MONTH_NUMBERS.get(found.group(1).lower()[:3])
    return f"{found.group(3)}-{month:02d}-{int(found.group(2)):02d}" if month else ""


def trip_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # A question on a trip the notes hold: those notes alone, leaving out any filed after a date it asks about. Whether a
    # country it names was part of the trip is the model's to read.
    notes, _ = trip_chain(message, pairs)
    if not notes:
        return None
    read = read_form(message)
    asked = asked_day(read)
    # The note that says which trip this is stays, whenever it was filed: without it the others do not name the trip.
    held = [pair for pair in notes if not asked or pair.timestamp[:10] <= asked or TRIP_HEAD_RE.search(pair.prompt)]
    lines = "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in held)
    routed = guide_records.record_notes(message)
    absent = [] if guide_records.LEG_NOTE in routed or guide_records.PREVIOUS_LEG_NOTE in routed or guide_records.asks_whole_trip(fold(read)) else [guide_records.LEG_NOTE]
    closing = TRIP_TOTAL_LINE if guide_records.asks_whole_trip(fold(read)) else TRIP_DATED_LINE if asked else ""
    return EvidenceView(f"{TRIP_HEADER}\n{lines}", [TRIP_READ_NOTE, *absent, *routed], closing=closing) if held else None


def invoice_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # A question on the invoice of a project it names in quotes: every short note on that project's one payables record, with
    # the day each was filed, leaving out those filed after a date the message asks about.
    read = read_form(message)
    name = QUOTE_RE.search(message)
    if not name or not INVOICE_ASK_RE.search(read):
        return None
    wanted = next(group for group in name.groups() if group).lower()
    short = [pair for pair in pairs if len(pair.prompt) < ACCOUNT_NOTE_CHARS + 100]
    codes = {code for pair in short if wanted in pair.prompt.lower() or wanted in read_form(pair.prompt).lower() for code in PAYABLES_RE.findall(pair.prompt)}
    if len(codes) != 1:
        return None
    code = next(iter(codes))
    held = by_date([pair for pair in short if code in pair.prompt])
    asked = asked_day(read)
    if asked:
        # The note that says which project this record is stays, whenever it was filed: without it the others do not name the project.
        held = [pair for pair in held if pair.timestamp[:10] <= asked or not FIGURE_MONEY_RE.search(pair.prompt)]
    if not any(FIGURE_MONEY_RE.search(pair.prompt) for pair in held):
        return None
    lines = "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in held)
    return EvidenceView(f"{PAYABLES_HEADER}\n{lines}", [PAYABLES_NOTE, *guide_records.record_notes(message)])


def handle_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # A messaging handle asked of a person the notes speak of: that person's short notes, all of them, with the day each was filed.
    if not guide_records.asks_handle(message) or not names_a_person(message):
        return None
    names = [name for name in dict.fromkeys(FULL_NAME_RE.findall(message)) if name.split()[0].lower() not in ORDINARY_OPENERS]
    if not names:
        return None
    asked, card = next(((name, card) for name in names if (card := person_card(name, pairs))), ("", []))
    if not any(HANDLE_WORD_RE.search(read_form(pair.prompt)) for pair in card):
        return None
    # A note that retires the handle stands over the notes before it that give one, as a change does over a plain statement. A
    # handle given after it stays.
    dated = by_date(card)
    retired = next((at for at in range(len(dated) - 1, -1, -1) if HANDLE_WORD_RE.search(read_form(dated[at].prompt)) and HANDLE_RETIRED_RE.search(read_form(dated[at].prompt))), -1)
    kept = [pair for at, pair in enumerate(dated) if at >= retired or not HANDLE_WORD_RE.search(read_form(pair.prompt))]
    lines = "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in kept)
    return EvidenceView(HANDLE_SHOWN.format(asked=asked, notes=lines), guide_records.record_notes(message), closing=HANDLE_DROPPED_LINE)


def dated_email_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # The notes that give a person's email, each with the day it was filed, for a question on the email as it stood on a date.
    lead = guide_records.dated_emails(message, pairs)
    if not lead or not guide_records.ASKED_DATE_RE.search(read_form(message)):
        return None
    return EvidenceView(lead, [DATED_EMAIL_NOTE])


def contact_sentence_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # A contact detail asked for the project the message puts in quotes: the sentences of the short notes that name that project and
    # give an address, each with the day its note was filed, oldest first, where a capitalised word of the sentence is also in the
    # message. Which of them answers is the model's to read.
    read = read_form(message)
    quoted = [next(group for group in found if group).lower() for found in QUOTE_RE.findall(message)]
    if not quoted or not CONTACT_ASK_WORD_RE.search(read) or not (guide_records.asks_contact_detail(message) or CONTACT_ASKS_RE.search(read)) or OWED_ASK_RE.search(read) or INVOICE_RE.search(message):
        return None
    seen: list[str] = []
    for pair in by_date([pair for pair in pairs if len(pair.prompt) < ACCOUNT_NOTE_CHARS]):
        for sentence in SENTENCE_SPLIT_RE.split(pair.prompt):
            low = sentence.lower()
            if guide_records.EMAIL_RE.search(sentence) and any(name in low for name in quoted) and any(word in message for word in PARTY_WORD_RE.findall(sentence)):
                line = f"- {pair.timestamp[:10]}: {sentence.strip()}"
                if line not in seen:
                    seen.append(line)
    if not seen:
        return None
    earlier = guide_rules._found(guide_rules.EARLIER_CONTACT_RE, message)
    return EvidenceView(CONTACT_SHOWN.format(notes="\n".join(seen)), [guide_rules.CONTACT_EARLIER_NOTE if earlier else CONTACT_NOTE, *guide_records.record_notes(message)])


# "Which two bakeries does Mia Pulley love?", "Which trails does Petra Heathcote hike? Name the two.", "Name both cafes Mia Pulley goes to":
# several things asked of one person the notes also call by another name. The notes that write either name are few and short, while
# the whole packet runs to dozens of records in which the second item sits under the other name, so those notes are shown alone, each
# whole (a long one by its sentences that write a name, with the sentence after each).
SEVERAL_OF_RE = re.compile(r"\b(?:two|three|four|both)\b|^\s*(?:Which|What)\s+[a-z][a-z' -]{1,30}s\s+(?:does|do|did|is|are|was|were|has|have|had)\b|^\s*What\s+(?:does|did|has|have|is)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b")
NOT_A_LIST_ASK_RE = re.compile(r"\b(?:e-?mail|address|handle|phone|number|invoice|owed?|balance|case file|thread|in order)\b", re.IGNORECASE)
SEVERAL_MAX_CHARS = 200
TIED_MAX_NOTES = 28
TIED_LONG_NOTE = 700
TIED_SHOWN = "The user's notes that write one of these names, found by code; not checked: {names}. Code took them for one person because a note ties them ({ties}) and may be wrong; a note that writes only a name resembling one of them is left out as someone else's. The notes, oldest first:\n{notes}"
TIED_NOTE = "The message asks for more than one thing of one person. In these notes each is written under one of that person's names, the full name or the other name a note ties to them, and usually in different notes, so read every note above before you answer; a note that says one thing replaced another for them leaves only the newer one, something a note puts in the past (used to, no longer, gave up) is not theirs now, and something a note only reports about a differently named person is not theirs. A note that says they love, like, swear by, are a regular at, are obsessed with, go to or keep going back to a place says what the message asks, whichever of those words the message uses, so each such place counts. Give every item you find, each as its note writes it, all on the one line 'ANSWER: <item> and <item>', as many as you found. If you find fewer than the message asks for, give only those and write nothing at all about the rest: not 'not stated', 'unknown', 'none', 'no other' or 'no record'."
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
CAPITAL_RUN_RE = re.compile(r"[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)*")
ROLE_HELD_RE = re.compile(r"\bis (?:now )?(?:the|our) (?:new )?([A-Za-z][A-Za-z' -]{5,60}?)[.,;]")
CALLED_CUE_RE = re.compile(r"\b(?:goes by|go by|gone by|went by|knows? [^.?!]{1,60}? as|they mean|calls?|called|known as|nicknamed?|answers to|signs [a-z ]{0,20}as)\b")


# Initials a person goes by ("has gone by S.B.", "everybody calls F.C."): a called name that is no capitalised word.
INITIALS_RE = re.compile(r"(?<![\w.])((?:[A-Z]\.){2,3})(?!\w)")


def initials_ties(index: UserIndex, full: str) -> dict[str, list[str]]:
    """Initials that a short note writing the full name, with a called-name cue, gives the person: one set of initials in that note."""
    ties: dict[str, list[str]] = {}
    for pid in index.nodes:
        text = coverage.short_prompt(index, pid)
        if text and coverage.mention(text, full) and CALLED_CUE_RE.search(text):
            found = list(dict.fromkeys(INITIALS_RE.findall(text)))
            if len(found) == 1:
                ties.setdefault(found[0], []).append(pid)
    return ties


def name_pattern(name: str) -> re.Pattern[str]:
    if name.endswith("."):
        return re.compile(r"(?<![\w.])" + re.escape(name))
    return re.compile(r"\b" + re.escape(name) + r"\b")


def lone_names(index: UserIndex, text: str, parts: set[str]) -> list[str]:
    """Capitalised words of a short note that stand alone (not inside a longer capitalised phrase once the person's own name is set aside), that the store never writes in lower case and writes capitalised in more than one conversation: names, not sentence openers, ordinary words or parts of a title."""
    found = []
    for run in CAPITAL_RUN_RE.findall(text):
        words = [word.rstrip("'’s") if word.endswith(("'s", "’s")) else word for word in run.split()]
        rest = [word for word in words if word not in parts]
        if len(rest) != 1:
            continue
        word = rest[0]
        if re.fullmatch(r"[A-Z][a-z]{1,20}", word) and word not in coverage.NOT_NAMES and word not in coverage.SENTENCE_START and word.lower() not in coverage.STOPWORDS and index.lower_df[word.lower()] == 0 and index.cap_df[word.lower()] > 1 and word not in found:
            found.append(word)
    return found


def person_ties(index: UserIndex, message: str, full: str) -> dict[str, list[str]]:
    """Other names the short notes give the person the message names in full, each with the notes that say so: the called-name search (M48); a short note writing the full name beside one lone name; where no other full name in the store shares the first name, a short note that writes the first name alone with a called-name cue and one lone name; and a short note opening with a role another short note says the person holds, with a called-name cue and one lone name."""
    parts = set(full.split())
    first = full.split()[0]
    ties: dict[str, list[str]] = {alias: list(stated) for alias, (name, stated) in alias_ties(index, message).items() if name == full}
    if ties:
        for initials, stated in initials_ties(index, full).items():
            ties.setdefault(initials, []).extend(stated)
        return ties
    shorts = [(pid, coverage.short_prompt(index, pid)) for pid in index.nodes]
    shorts = [(pid, text) for pid, text in shorts if text]
    # A lone name counts only where the notes also use it as someone: another short note opens with it.
    opens = {text.split()[0].strip(",.;:!?\"'") for _, text in shorts if text.split()}
    # Another full name with the same first name makes a bare first name ambiguous; "calls Konstantin Pep" is a called name, not a surname.
    first_is_theirs = not any(other.split()[0] == first and other != full for _, text in shorts if not CALLED_CUE_RE.search(text) for other in FULL_NAME_RE.findall(text))
    roles: list[str] = []
    for pid, text in shorts:
        if coverage.mention(text, full):
            names = [name for name in lone_names(index, text, parts) if name in opens]
            if len(names) == 1:
                ties.setdefault(names[0], []).append(pid)
            roles += [role.strip() for role in ROLE_HELD_RE.findall(text)]
        elif first_is_theirs and coverage.mention(text, first) and CALLED_CUE_RE.search(text):
            names = [name for name in lone_names(index, text, parts) if name in opens]
            if len(names) == 1:
                ties.setdefault(names[0], []).append(pid)
    for role in roles:
        opening = re.compile(r"^\s*(?:The|Our)\s+" + re.escape(role) + r"\b", re.IGNORECASE)
        for pid, text in shorts:
            if opening.search(text) and CALLED_CUE_RE.search(text):
                names = [name for name in lone_names(index, text, parts) if name in opens]
                if len(names) == 1:
                    ties.setdefault(names[0], []).append(pid)
    for initials, stated in initials_ties(index, full).items():
        ties.setdefault(initials, []).extend(stated)
    return {alias: list(dict.fromkeys(stated)) for alias, stated in ties.items() if len(coverage.name_holders(index, alias)) <= coverage.MAX_SURNAME_HOLDERS}


# A capitalised phrase of two to six words: a place or thing a note names ("Pinehaven Bread Room").
NAMED_THING_RE = re.compile(r"\b[A-Z][\w'’&-]*(?:\s+(?:of|the|and|on|de|la)?\s*[A-Z][\w'’&-]*){1,5}")
PAST_CUE_RE = re.compile(r"\b(?:used to|no longer|gave up|stopped|anymore|any more|replaced|instead of|switched from|before)\b", re.IGNORECASE)
WORK_CUE_RE = re.compile(r"\b(?:works? (?:as|at|for)|employed|job at|joined|hired by|colleague|manager at|lead at)\b", re.IGNORECASE)
TIED_READ = "Code read off each note above whose subject is this person, under one of these names, the place or thing it names; not checked, and the notes decide:\n{things}"


ASKED_COUNT = {"two": 2, "both": 2, "three": 3, "four": 4}
ASKED_COUNT_RE = re.compile(r"\b(two|both|three|four)\b")


def things_named(text: str, patterns: list[re.Pattern[str]], names: list[str]) -> list[str]:
    """The capitalised phrases a note names after one of the person's names when that name is the note's subject: not a
    possessive ("X's sibling ... loves Y" is the sibling's), not in a note that puts it in the past, not a name of the person."""
    if PAST_CUE_RE.search(text) or WORK_CUE_RE.search(text):
        return []
    found: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            after = text[match.end():]
            if after[:2] in ("'s", "’s"):
                continue
            for thing in NAMED_THING_RE.findall(after.split(". ")[0]):
                thing = thing.strip()
                if not any(name in thing or thing in name for name in names) and thing not in found:
                    found.append(thing)
    return found


def tied_names_view(message: str, index: UserIndex) -> EvidenceView | None:
    if len(message) > SEVERAL_MAX_CHARS or not SEVERAL_OF_RE.search(message) or NOT_A_LIST_ASK_RE.search(message):
        return None
    fulls = [name for name in dict.fromkeys(FULL_NAME_RE.findall(message)) if name.split()[0].lower() not in ORDINARY_OPENERS]
    if len(fulls) > 1:
        return None
    if fulls:
        ties = person_ties(index, message, fulls[0])
        tied = "; ".join(f"{alias} = {fulls[0]}" for alias in ties)
        names = [fulls[0], *ties]
    else:
        # A one-word name: the names the called-name search reaches for it, over a surname where the notes give one.
        found = alias_ties(index, message)
        ties = {alias: list(stated) for alias, (name, stated) in found.items()}
        tied = "; ".join(f"{alias} = {name}" for alias, (name, _) in found.items())
        names = list(dict.fromkeys(name for alias, (full, _) in found.items() for name in (full, alias)))
    if not ties:
        return None
    patterns = [name_pattern(name) for name in names]
    stated = {pid for pids in ties.values() for pid in pids}
    held = [node.pair for pid, node in index.nodes.items() if pid in stated or any(pattern.search(node.pair.prompt) for pattern in patterns)]
    if not 2 <= len(held) <= TIED_MAX_NOTES:
        return None
    lines = []
    things: list[str] = []
    for pair in sorted(held, key=lambda pair: (pair.timestamp, pair.pair_id)):
        text = pair.prompt.strip()
        for thing in things_named(text, patterns, names) if len(text) <= TIED_LONG_NOTE else []:
            things.append(f"- {pair.timestamp[:10]}: {thing}")
        if len(text) > TIED_LONG_NOTE:
            sentences = SENTENCE_END_RE.split(text)
            keep = sorted({place for position, sentence in enumerate(sentences) if any(pattern.search(sentence) for pattern in patterns) for place in (position, position + 1) if place < len(sentences)})
            text = " ... ".join(sentences[place] for place in keep)
        lines.append(f"- {pair.timestamp[:10]}: {text}")
    shown = TIED_SHOWN.format(names=", ".join(names), ties=tied, notes="\n".join(lines))
    asked = ASKED_COUNT.get(next(iter(ASKED_COUNT_RE.findall(message.lower())), ""), 0)
    named = [thing.split(": ", 1)[1] for thing in things]
    # Shown only when it reads cleanly: as many things as the message asks for, none written twice.
    if asked and len(named) == asked and len(set(named)) == asked:
        shown += "\n\n" + TIED_READ.format(things="\n".join(things))
    return EvidenceView(shown, [TIED_NOTE], list_ask=True)


def evidence_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    return partial_view(message, pairs) or invoice_view(message, pairs) or trip_view(message, pairs) or handle_view(message, pairs) or dated_email_view(message, pairs) or no_email_view(message, pairs) or contact_sentence_view(message, pairs)


async def answer_from_view(engine: RecordsEngine, req: RunRequest, view: EvidenceView, effort: str, max_tokens: int, deadline: float, outcome: Outcome) -> bool:
    base = VIEW_SYSTEM.replace(f" {NOT_STATED_LINE}", "") if view.list_ask else VIEW_SYSTEM
    system = short_system(req.system_prompt, " ".join([base, *view.notes]))
    user = f"{view.shown}\n\n{MESSAGE_HEADER}\n{req.user_input}" + (f"\n\n{view.closing}" if view.closing else "")
    outcome.events.append("evidence view")
    return await decide(engine, req, [{"role": "system", "content": system}, {"role": "user", "content": user}], effort, view.max_tokens or max_tokens, deadline, outcome)
