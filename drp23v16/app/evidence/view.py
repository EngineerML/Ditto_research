"""Evidence views: one deciding call over the short dated notes that name what a question asks about.

Taken from Hades v24 (agent a0fc00a9, released 2026-11-04 22:18 UTC; the views first shipped in Hades v20), app/short.py:
the view constants, names_a_person, EvidenceView .. answer_from_view. The helpers it reads (guide_spelling, guide_records,
people, english_words) are that release's files, copied beside this one. The deciding call is this harness's own
short.decide (no drafts, no follow-up question).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..action import VALUE_VERBATIM, Outcome
from ..protocol import MemoryPair, RunRequest
from ..records import RecordsEngine
from ..short import MESSAGE_HEADER, decide, short_system
from . import guide_records
from .english_words import WORDS
from .guide_spelling import SHORT_WORDS, SpellingKey, fold, read_form
from .people import FULL_NAME_RE, ORDINARY_OPENERS, by_date, no_email_held, person_card

QUOTE_RE = re.compile(r"“([^”\n]{2,60})”|\"([^\"\n]{2,60})\"|‘([^’\n]{2,60})’")
SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
ONE_LINE_ANSWER = "Reply with one line only, beginning 'ANSWER: ', with only the value asked for, as short as the notes put it, in their words; when several things are asked, give them on that line in the order asked, separated by ' ; '. Do all your working before you reply and write none of it: no figure or date the message did not ask for, not even those the answer was worked out from, and any money figure to its two decimal places."
NOT_STATED_LINE = "If the notes do not state something asked, say so on that line, with what they do hold on it."
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {ONE_LINE_ANSWER} Write any date in full, with day, month and year. A thread that was finished, dropped or cancelled still has the last person who held it and the last next action a note gave. {NOT_STATED_LINE}"

ACCOUNT_NOTE_CHARS = 600
NO_EMAIL_NOTE = "An address asked for here is an email address. If one of these notes gives a work email for the person the message asks about, give it. Only if none does: tell the user you have no record of a work email for that person, and in the same reply who the notes do hold: each of the people named at the top of these notes as the ones they hold, by full name with their role, employer and city as the notes give them, as a different person where the name differs, and not the person asked about unless named there, with no email address of anyone, not even one of theirs, all on the one line: 'ANSWER: I have no record of a work email for <the person asked about>; the notes hold <full name>, <role> at <employer> in <city>'."
EMAIL_HELD_LINE = "If a note above gives an email address for the person asked about, under any name they go by and even with a word in it misspelt, the ANSWER line is that address; only if none does, say you have no record."
NO_EMAIL_SHOWN = "The user's short notes naming {asked}, and any nickname those notes give them, found by code; not checked. The people these notes hold that this message points to: {people}. The notes:\n{notes}"
SAVED_EMAIL_ASK_RE = re.compile(r"\b(?:which|what)\b[^.?]{0,40}\b(?:email|address)\b[^.?]{0,40}\b(?:did i|do i)\b", re.IGNORECASE)
NO_EMAIL_MAX_NOTES = 16
INVOICE_RE = re.compile(r"\b(?:INV|AP)-[A-Z0-9]+\b")
OWED_ASK_RE = re.compile(r"\b(?:owe|owed|owing|balance|remains?|outstanding|left)\b", re.IGNORECASE)
INVOICE_HEADER = "The user's saved notes on the invoice this message names, found by code; not checked:"
TRIP_CHAIN_CHARS = 450
TRIP_PLACE_RE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
TRIP_HEAD_RE = re.compile(r"\bOur ([a-z]+(?: [a-z]+){0,3}) was\b")
TRIP_PERSON_RE = re.compile(r"\b([A-Z][a-z]+) and I\b")
ASKED_DAY_RE = re.compile(r"\b(jan\w*|feb\w*|mar\w*|apr\w*|may|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*)\s+(\d{1,2}),?\s+(20\d\d)\b", re.IGNORECASE)
MONTH_NUMBERS = {name: number for number, name in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1)}
TRIP_READ_NOTE = "Read these notes in order: the first plan, then each change to it. Work out each stay from the plan and the changes the notes give before you reply, and give the one thing the message asks for."
TRIP_DATED_LINE = "The days are the first plan's with every change in the notes shown above applied."
TRIP_TOTAL_LINE = "Reply with the total alone: 'ANSWER: <total> days'."
TRIP_HEADER = "The user's saved notes on this trip, found by code from its name, oldest first, each after the day it was filed; not checked:"
PAYABLES_NOTE = "The latest total in these notes is the total, whatever an earlier note gave. A payment stays as written unless a note changes it. What remains is that total less the amount paid."
PAYABLES_HEADER = "The user's saved notes on this project's payables record, found by code from the project's name, each after the day it was filed; not checked:"
INVOICE_ASK_RE = re.compile(r"\b(?:invoice|bill|owe|owed|owing|balance|remains?|outstanding)\b", re.IGNORECASE)
PAYABLES_RE = re.compile(r"\bAP-[A-Z0-9]+\b")
FIGURE_MONEY_RE = re.compile(r"[$€£]\s?\d")
HANDLE_SHOWN = "The user's short notes on {asked}, found by code; not checked:\n{notes}"
HANDLE_WORD_RE = re.compile(r"\b(?:signal|whatsapp|telegram|handle)\b", re.IGNORECASE)
HANDLE_RETIRED_RE = re.compile(r"\b(?:retired|remove|removed|drop|dropped|closed that account|no longer use|stopped using|deleted)\b", re.IGNORECASE)
DATED_EMAIL_LINE = "Every note above is about this person, whichever name it uses: the answer is the address in the last of them filed on or before that date."
DATED_EMAIL_NOTE = "Read the day before each note above against the date the message asks about, and give the address your reading leaves on file then, with nothing about other dates, ending with the line 'ANSWER: <that email>'. If none was on file yet, say so."


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


@dataclass(frozen=True)
class EvidenceView:
    shown: str
    notes: list[str]
    max_tokens: int = 0
    closing: str = ""


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
    absent = [] if guide_records.LEG_NOTE in routed or guide_records.asks_whole_trip(fold(read)) else [guide_records.LEG_NOTE]
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
    return EvidenceView(HANDLE_SHOWN.format(asked=asked, notes=lines), guide_records.record_notes(message))


def dated_email_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    # The notes that give a person's email, each with the day it was filed, for a question on the email as it stood on a date.
    lead = guide_records.dated_emails(message, pairs)
    if not lead or not guide_records.ASKED_DATE_RE.search(read_form(message)):
        return None
    return EvidenceView(lead, [DATED_EMAIL_NOTE], closing=DATED_EMAIL_LINE)


def evidence_view(message: str, pairs: list[MemoryPair]) -> EvidenceView | None:
    return partial_view(message, pairs) or invoice_view(message, pairs) or trip_view(message, pairs) or handle_view(message, pairs) or dated_email_view(message, pairs) or no_email_view(message, pairs)


async def answer_from_view(engine: RecordsEngine, req: RunRequest, view: EvidenceView, pairs: list[MemoryPair], effort: str, max_tokens: int, deadline: float, outcome: Outcome) -> bool:
    system = short_system(req.system_prompt, " ".join([TOPIC_SYSTEM, *view.notes]))
    key = SpellingKey([pair.prompt for pair in pairs]).lines([view.shown])
    user = f"{view.shown}" + (f"\n\n{key}" if key else "") + f"\n\n{MESSAGE_HEADER}\n{req.user_input}" + (f"\n\n{view.closing}" if view.closing else "")
    outcome.events.append("evidence view")
    return await decide(engine, req, [{"role": "system", "content": system}, {"role": "user", "content": user}], effort, view.max_tokens or max_tokens, deadline, outcome)
