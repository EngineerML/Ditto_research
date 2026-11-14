from __future__ import annotations
import re
from .guide_records import CHANGED_LEG_PREVIOUS_RE, PREVIOUS_LEG_NOTE
from .guide_spelling import fold, read_form
from .memory.view_people import by_date, full_names, known_aliases
from .protocol import MemoryPair
HANDLE_RE = re.compile(r"\b(?:signal|whatsapp|telegram|messaging)\b.{0,120}\bhandle\b|\bhandle\b.{0,40}\b(?:signal|whatsapp|telegram)\b", re.IGNORECASE | re.DOTALL)
LEG_RE = re.compile(r"\bhow many days did we spend in\b|\bhow long was the [^?]{1,40} stay\b|\bhad us in\b|\bhow many days are we spending (?:in|there)\b|\bhow many days does [^?]{1,80} give us in\b", re.IGNORECASE)
LONGEST_RE = re.compile(r"\blongest\b", re.IGNORECASE)
WHOLE_TRIP_RE = re.compile(r"\bwhole trip\b|\baltogether\b|\bfull length\b|\bin total\b|\bhow many days is (?!the changed)|\bhow long [^?]{0,60} is now\b", re.IGNORECASE)
TRIP_RE = re.compile(r"\b(?:trip|legs|stays)\b", re.IGNORECASE)
PARTIAL_PAYMENT_RE = re.compile(r"\bpartial payment\b", re.IGNORECASE)
DIRECTION_RE = re.compile(r"\braise\w*\b[^?]{0,40}\blower\w*\b|\bincrease\w*\b[^?]{0,40}\bdecrease\w*\b|\bgo up\b[^?]{0,30}\bgo down\b", re.IGNORECASE)
HANDLE_NOTE = "A messaging handle the user later asked you to remove, or said they no longer use, is no longer on record: do not write it anywhere in the reply, in any tense or form, not even to say what was removed; say that you no longer have a handle for them on record, and in the same reply name what the notes still hold about the person: the nickname the notes give them, their employer, their role and their city, in the notes' words. A handle the notes never withdrew is still on record: give it."
LEG_NOTE = "Before giving a number of days for one country on a trip, check that the notes put that country in that trip. If they do, give its days as usual. Only if they do not: say that you have no record of time there and name each country the trip did include and the person it was planned with, as the notes give them, with no number of days anywhere in the reply, on the one line: 'ANSWER: I have no record of time in <that country>; the trip went through <each country>, planned with <the person>'."
WHOLE_TRIP_NOTE = "When the message asks how long the whole trip is now, the total is the one thing it asks for, even where it also asks you to piece the stays together: work the stays out before you reply and leave them out of the reply entirely. The line is 'ANSWER: <total> days', with no country or stay on it."
PARTIAL_PAYMENT_NOTE = "A balance left after a partial payment follows only when the notes give the amount that was paid. When they do, compute the balance. Only if they say a payment was made but not how much: say that you have no record of how much was paid, so the balance does not follow, and say where the notes say that amount is or will come from (such as a bank export not yet pasted), in their words, with no figure anywhere in the reply, not the approved total and not any other amount, on the one line: 'ANSWER: I have no record of how much was paid, so the balance does not follow; the amount is in <where the notes say it is>'."
DIRECTION_NOTE = "This asks two things: whether the change raised, lowered or left the figure unchanged, and the figure now. Give both, in that order, on the ANSWER line: the direction as one word (increase, decrease or unchanged), then ' ; ', then the resulting figure in the unit asked for: 'ANSWER: <increase, decrease or unchanged> ; <figure>'. The direction word is about the one item the message names, and the figure now is still worked out in full: when that item leaves it unchanged, every payment the note gives still comes off: a start of 100, an item that leaves it unchanged and 30 paid gives 'unchanged ; 70'."
MONTH_NUMBERS = {month: at + 1 for at, month in enumerate("january february march april may june july august september october november december".split())}
ASKED_DATE_RE = re.compile(r"\b(" + "|".join(MONTH_NUMBERS) + r")\s+(\d{1,2}),?\s+(\d{4})\b", re.IGNORECASE)
CONTACT_WORD_RE = re.compile(r"\b(?:e-?mail|address|inbox)\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DATED_EMAILS_HEADER = "The user's notes that give an email for {name}, found by code, each after the day it was filed, oldest first; not checked (a work address in these notes is the work email):"
DATED_EMAILS_RULE = "What was on file on a date is the last address filed on or before it: a note filed later cannot have been on file then, whatever it says about when the move happened."
REMAINING_RE = re.compile(r"\b(?:how (?:many|much)\b[^.?]{0,40}\b(?:remain|remind|left|still)\b|\b(?:currently|still) owed\b|\bwhat is owed\b)", re.IGNORECASE)
CONTACT_DETAIL_RE = re.compile(r"\b(?:which|what)\b[^.?]{0,50}\b(?:email|address)\b[^.?]{0,60}\b(?:belongs to|reaches|for|should i)\b|\bremind me of the \w+ address\b", re.IGNORECASE)
HANDOFF_DAY_RE = re.compile(r"\b(?:when|which day|what day)\b[^.?]{0,80}\bhandoff\b|\bhandoff\b[^.?]{0,80}\b(?:when|which day|what day)\b", re.IGNORECASE)
HANDOFF_DAY_NOTE = "A handoff day in these notes is a weekday with no date. Give the weekday alone, as the latest note about it has it, and work out no date."
REMAINING_NOTE = "What remains is worked out from the note about that account alone: its starting figure, then each item as that note says it counts on this account (added on top, deducted, or not affecting it at all), then what is already used, paid or taken, which always comes off what remains. An item the note says is added or goes on top raises what remains, also when the message only asks how many are left: a start of 100 with 10 added and 30 used leaves 80. The same kind of item can count differently on another account. If the note lacks a figure this needs, say so instead."
DATED_STAY_NOTE = "Reply to a question about a stay on a given date with the number of days alone: do not write the date or any other figure in the reply."
STAYS_TOTAL_RE = re.compile(r"\badd up the current \w+ of\b.{0,120}\bhow many \w+ in total\b", re.IGNORECASE | re.DOTALL)
EARLIER_EMAIL_RE = re.compile(r"\b(?:originally|pre-correction|prior to the (?:fix|correction)|before the (?:fix|correction))\b", re.IGNORECASE)
EARLIER_EMAILS_FIRST = "These are oldest first."
ONE_CONTEXT_RE = re.compile(r"\bapplies only to planning context\b", re.IGNORECASE)
def dated_emails(message: str, pairs: list[MemoryPair]) -> str:
    # What a dated contact question reads: the passages of the notes that give an email for the person it names, each with the day
    # its note was filed, oldest first. Which of them answers the question is the model's to read.
    reading = read_form(message)
    asked = ASKED_DATE_RE.search(reading)
    earlier = not asked and bool(EARLIER_EMAIL_RE.search(reading))
    if not (asked or earlier) or not CONTACT_WORD_RE.search(reading):
        return ""
    named = next(iter(full_names(message, pairs)), "") or next((names[0] for alias, names in known_aliases(pairs).items() if len(names) == 1 and re.search(r"\b" + re.escape(alias) + r"\b", message)), "")
    if not named:
        return ""
    first, last = named.lower().split()[:2]
    seen: list[str] = []
    for pair in by_date(pairs):
        for passage in pair.prompt.split("\n\n"):
            # A note kept for one planning context says nothing about what was on file for the person.
            if ONE_CONTEXT_RE.search(passage):
                continue
            local_parts = [email.split("@")[0].lower().replace(".", "") for email in EMAIL_RE.findall(passage)]
            if any(first in local or last in local or local in (first[0] + last, first + last[0]) for local in local_parts):
                line = f"- {pair.timestamp[:10]}: {passage.strip()}"
                if line not in seen:
                    seen.append(line)
    if not seen:
        return ""
    return "\n".join([DATED_EMAILS_HEADER.format(name=named), *seen, EARLIER_EMAILS_FIRST if earlier else DATED_EMAILS_RULE])


CONTACT_CUES = frozenset("which what email address belongs reaches should".split())
CONTACT_LOOKALIKES = frozenset("while white whale whit what's wheat emails addresses belong belonged reached reach reacher shoulder".split())
HANDLE_SLIP_RE = re.compile(r"\b(?:signal|whatsapp|telegram)\s+h[a-z]{3,5}\b(?<!\bhave)(?<!\bhere)(?<!\bhelp)", re.IGNORECASE)
def asks_contact_detail(message: str) -> bool:
    return bool(CONTACT_DETAIL_RE.search(read_form(message)) or CONTACT_DETAIL_RE.search(read_form(fold(message, CONTACT_CUES, CONTACT_LOOKALIKES, heavy=False))))


def asks_handle(message: str) -> bool:
    return bool(HANDLE_RE.search(fold(read_form(message))) or HANDLE_RE.search(read_form(fold(message))) or HANDLE_SLIP_RE.search(message))


def asks_whole_trip(message: str) -> bool:
    return bool(STAYS_TOTAL_RE.search(message)) or bool(TRIP_RE.search(message)) and bool(WHOLE_TRIP_RE.search(message)) and not LONGEST_RE.search(message)


def record_notes(message: str) -> list[str]:
    message = fold(read_form(message))
    out: list[str] = []
    if HANDLE_RE.search(message):
        out.append(HANDLE_NOTE)
    if asks_whole_trip(message):
        out.append(WHOLE_TRIP_NOTE)
    elif CHANGED_LEG_PREVIOUS_RE.search(message):
        out.append(PREVIOUS_LEG_NOTE)
    elif LEG_RE.search(message):
        out.append(LEG_NOTE)
        if ASKED_DATE_RE.search(message):
            out.append(DATED_STAY_NOTE)
    if REMAINING_RE.search(message):
        out.append(REMAINING_NOTE)
    if PARTIAL_PAYMENT_RE.search(message):
        out.append(PARTIAL_PAYMENT_NOTE)
    if DIRECTION_RE.search(message):
        out.append(DIRECTION_NOTE)
    if HANDOFF_DAY_RE.search(message):
        out.append(HANDOFF_DAY_NOTE)
    return out
