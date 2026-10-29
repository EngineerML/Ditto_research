from __future__ import annotations

import re
from dataclasses import dataclass

NEXT_STEP_RE = re.compile(r"\bnext\b[^?.]{0,40}\b(?:step|move|action)\b|\b(?:open|pending) action\b|\bowes? the next\b|\bhas the ball\b|\bmeant to act next\b|\bwhat comes next\b|\bwaiting to happen\b|\bdoing what next\b|\bwho is doing what\b", re.IGNORECASE)
CONTACT_RE = re.compile(r"\b(?:e-?mail|work address|mail address)\b", re.IGNORECASE)
HOLDER_RE = re.compile(r"\b(?:owns?|owned|owner|running|runs|run it|holding|holds|has it|has the thread|accountable|responsible|on point|chase|in charge|whose is it)\b", re.IGNORECASE)
WHO_RE = re.compile(r"\b(?:who|whose|whoever|person|whom)\b", re.IGNORECASE)
STANDING_RE = re.compile(r"\b(?:where are we|stand|stands|state|status|position|landed|land|standing)\b", re.IGNORECASE)
FIGURE_RE = re.compile(r"\b(?:figure|total|how many|number|amount|work out|money|percent|seats|days|nights|hours|guests|items|units)\b", re.IGNORECASE)
CHANGED_RE = re.compile(r"\b(?:now|after|change\w*|adjust\w*|apply|follow\w*|final|arriv\w*|result\w*|land\w*|work out|come to)\b", re.IGNORECASE)
LESSON_RE = re.compile(r"\b(?:take away|took away|takeaway|lesson|remember next time|rule did i set|teach\w*|resolve\w* to do differently|advice i kept|learn\w*|moral|stuck with me)\b", re.IGNORECASE)
ENDED_RE = re.compile(r"\b(?:end up|ended up|where it is|state of play)\b", re.IGNORECASE)
OPENING_QUESTION_RE = re.compile(r"^\s*where are we with [^?]*\?\s*(?:the [^.?]* one\.)?", re.IGNORECASE)
HANDLE_RE = re.compile(r"\b(?:signal|whatsapp|telegram|messaging)\b.{0,120}\bhandle\b|\bhandle\b.{0,40}\b(?:signal|whatsapp|telegram)\b", re.IGNORECASE | re.DOTALL)
LEG_RE = re.compile(r"\bhow many days did we spend in\b|\bhow long was the [^?]{1,40} stay\b|\bhad us in\b|\bhow many days are we spending (?:in|there)\b|\bhow many days does [^?]{1,80} give us in\b", re.IGNORECASE)
LONGEST_RE = re.compile(r"\blongest\b", re.IGNORECASE)
WHOLE_TRIP_RE = re.compile(r"\bwhole trip\b|\baltogether\b|\bfull length\b|\bin total\b|\bhow many days is (?!the changed)|\bhow long [^?]{0,60} is now\b", re.IGNORECASE)
TRIP_RE = re.compile(r"\b(?:trip|legs|stays)\b", re.IGNORECASE)
PAYING_PARTY_RE = re.compile(r"\b(?:commission\w*|paying customer|pays us|the one we pay|supplier we pay|billing us|our client|our supplier)\b", re.IGNORECASE)
PARTIAL_PAYMENT_RE = re.compile(r"\bpartial payment\b", re.IGNORECASE)
AGREEMENT_RE = re.compile(r"\b(?:disagree\w*|clash\w*|line up|agree|consistent|match|each record|all of them|say different|say so|as far as the records go)\b", re.IGNORECASE)

OWNER_NOTE = "Who owns a piece of work changes only where a note puts someone in charge of it: it was handed or passed to someone, someone took it over or picked it up, someone is the owner now in place of another. A person a later note gives the next step, a task or the ball, and a firm the work moved to as its vendor or supplier, are not thereby its owner; the owner is the person named in the last such note, and stays its owner even when the work was later cancelled, dropped or finished: a status or a firm is never the answer to who owns it."
CONTACT_NOTE = "A person's current work email is the one the notes give for the employer they are at now; an address from before they moved is out of date."
NEXT_NOTE = "The next step is the one set by the latest note that gives the work a next action — a follow-up, or a handover with the new owner's first action. Give only that one step: on the ANSWER line, the person, then the task, then the channel, separated by ' ; ', each as short as the note puts it: the task without when or why, the channel alone, such as email, phone, chat or in person. Within one note, the passage that comes later holds; a later follow-up replaces the next action that came with a handover, and whoever owns the work is not always the one with the next step."
DISAGREE_NOTE = "When the notes give it different states, say that the records disagree. On the ANSWER line give each state in the one or two words the notes use for it, then the word disagree, separated by ' ; '."


HANDLE_NOTE = "A messaging handle the user later asked you to remove, or said they no longer use, is no longer on record: do not give it anywhere in the reply; say that you no longer have a handle for them on record, and say what the notes still hold about the person, such as their employer, role, city or work email. A handle the notes never withdrew is still on record: give it."
LEG_NOTE = "Before giving a number of days for one country on a trip, check that the notes put that country in that trip. If they do not, say that you have no record of time there, give no number of days, and name the countries the trip did include."
WHOLE_TRIP_NOTE = "When the message asks how long the whole trip is now, the total is the one thing it asks for, even where it also asks you to piece the stays together: work the stays out before you reply and leave them out of the reply; if you do mention them, write them as one plain sentence, not as a list. Reply with one sentence giving the total, then the line 'ANSWER: <total> days'."
SEVERAL_ON_ONE_LINE = 'when several things were asked, put them on that line in the order asked, separated by " and "'
TOTAL_ALONE = "when the message asks for a total, that line holds the total alone"
PARTIAL_PAYMENT_NOTE = "A balance left after a partial payment follows only when the notes give the amount that was paid. If they say a payment was made but not how much, say that you have no record of how much was paid, so the balance does not follow, and cite what the notes do give, such as the approved total and the payment record; the approved total is not the balance. When the notes do give the amount paid, compute the balance."

PAYING_PARTY_NOTE = "In these records the commissioning party, client or paying customer is the organisation that pays us for the work; the supplier or vendor is the organisation we pay, the one billing us. Find the field the batch defines for the party that pays us, and answer with its value, the organisation's name, not the field's label."

FIGURE_NOTE = "When an approval comes with a cap and the notes say how much of it has already gone out or is spoken for, the money figure is what is left: the cap less that amount. When a later note corrects a figure, the corrected one replaces the earlier one; when a note adds to or takes off a figure, apply that change to the figure it names. Compute the figure with the calculate tool and give that one figure on the ANSWER line."
LESSON_NOTE = "The lesson is the saying the user wrote down as what they took from it or will remember next time, often a proverb; a remark about where the note is filed or which note to read first is not the lesson. Give the saying in their words."
STATUS_NOTE = "This asks what state it is in now, not who has it: give the status the latest note about where it stands gives it, as one status word, spelled correctly even where the note misspells it."


@dataclass(frozen=True)
class Guide:
    asks_next_step: bool
    asks_holder: bool
    asks_contact: bool
    asks_disagreement: bool
    asks_figure: bool
    asks_lesson: bool
    asks_status: bool


def without_opening_question(message: str) -> str:
    rest = OPENING_QUESTION_RE.sub("", message, count=1)
    return rest if rest.strip() else message


def read(message: str) -> Guide:
    next_step = bool(NEXT_STEP_RE.search(message))
    holder = not next_step and bool(HOLDER_RE.search(message)) and (bool(WHO_RE.search(message)) or bool(CONTACT_RE.search(message)))
    contact = holder and bool(CONTACT_RE.search(message))
    disagreement = not next_step and not holder and bool(STANDING_RE.search(message)) and bool(AGREEMENT_RE.search(message))
    figure = not next_step and not holder and bool(FIGURE_RE.search(message)) and bool(CHANGED_RE.search(message))
    lesson = not next_step and not holder and bool(LESSON_RE.search(message))
    asked = without_opening_question(message)
    status = not next_step and not holder and not disagreement and not figure and not lesson and (bool(STANDING_RE.search(asked)) or bool(ENDED_RE.search(asked)))
    return Guide(next_step, holder, contact, disagreement, figure, lesson, status)


def asks_whole_trip(message: str) -> bool:
    return bool(TRIP_RE.search(message)) and bool(WHOLE_TRIP_RE.search(message)) and not LONGEST_RE.search(message)


def answer_line(system: str, message: str) -> str:
    return system.replace(SEVERAL_ON_ONE_LINE, TOTAL_ALONE, 1) if asks_whole_trip(message) else system


def record_notes(message: str) -> list[str]:
    out: list[str] = []
    if HANDLE_RE.search(message):
        out.append(HANDLE_NOTE)
    if asks_whole_trip(message):
        out.append(WHOLE_TRIP_NOTE)
    elif LEG_RE.search(message):
        out.append(LEG_NOTE)
    if PARTIAL_PAYMENT_RE.search(message):
        out.append(PARTIAL_PAYMENT_NOTE)
    return out


def program_notes(message: str) -> list[str]:
    return [PAYING_PARTY_NOTE] if PAYING_PARTY_RE.search(message) else []


def notes(message: str) -> list[str]:
    guide = read(message)
    out: list[str] = []
    if guide.asks_holder:
        out.append(OWNER_NOTE)
    if guide.asks_contact:
        out.append(CONTACT_NOTE)
    if guide.asks_next_step:
        out.append(NEXT_NOTE)
    if guide.asks_disagreement:
        out.append(DISAGREE_NOTE)
    if guide.asks_figure:
        out.append(FIGURE_NOTE)
    if guide.asks_lesson:
        out.append(LESSON_NOTE)
    if guide.asks_status:
        out.append(STATUS_NOTE)
    return out
