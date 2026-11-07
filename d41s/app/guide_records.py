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
LESSON_RE = re.compile(r"\b(?:take away|took away|takeaway|lesson|remember next time|rule did i set|teach|resolve\w* to do differently|advice i kept|learn\w*|moral|stuck with me)\b", re.IGNORECASE)
ENDED_RE = re.compile(r"\b(?:end up|ended up|where it is|state of play)\b", re.IGNORECASE)
OPENING_QUESTION_RE = re.compile(r"^\s*where are we with [^?]*\?\s*(?:the [^.?]* one\.)?", re.IGNORECASE)
EMAIL_RE = re.compile(r"\be-?mail\b", re.IGNORECASE)
HANDLE_RE = re.compile(r"\b(?:signal|whatsapp|telegram|messaging)\b.{0,120}\bhandle\b|\bhandle\b.{0,40}\b(?:signal|whatsapp|telegram)\b", re.IGNORECASE | re.DOTALL)
LEG_RE = re.compile(r"\bhow many days did we spend in\b|\bhow long was the [^?]{1,40} stay\b|\bhad us in\b|\bhow many days are we spending (?:in|there)\b|\bhow many days does [^?]{1,80} give us in\b", re.IGNORECASE)
LONGEST_RE = re.compile(r"\blongest\b", re.IGNORECASE)
WHOLE_TRIP_RE = re.compile(r"\bwhole trip\b|\baltogether\b|\bfull length\b|\bin total\b|\bhow many days is (?!the changed)|\bhow long [^?]{0,60} is now\b", re.IGNORECASE)
TRIP_RE = re.compile(r"\b(?:trip|legs|stays)\b", re.IGNORECASE)
STAY_RE = re.compile(r"\b(?:stays?|legs?)\b", re.IGNORECASE)
REVISED_RE = re.compile(r"\b(?:chang\w*|revis\w*)\b", re.IGNORECASE)
FIRST_PLAN_RE = re.compile(r"\b(?:first|original\w*|before)\b", re.IGNORECASE)
DAYS_ASKED_RE = re.compile(r"\b(?:days|long|length)\b", re.IGNORECASE)
NOW_RE = re.compile(r"\b(?:now|current\w*|updated)\b", re.IGNORECASE)
PAYING_PARTY_RE = re.compile(r"\b(?:commission\w*|paying customer|pays us|the one we pay|supplier we pay|billing us|our client|our supplier)\b", re.IGNORECASE)
PARTIAL_PAYMENT_RE = re.compile(r"\bpartial payment\b", re.IGNORECASE)
DIRECTION_RE = re.compile(r"\braise\b[^?]{0,40}\blower\b[^?]{0,60}\bunchanged\b", re.IGNORECASE)
SEQUENCE_RE = re.compile(r"\b(?:came first|replaced it|the replacement|took over|in order|in the order|sequence of|history in order|earliest first|oldest to newest|change hands|then current|then second|which was which)\b", re.IGNORECASE)
SEQUENCE_KIND_RE = re.compile(r"\b(vendor|supplier|hotel|venue|clinic|contractor|club|moving compan(?:y|ie)|service)s?\b", re.IGNORECASE)
AGREEMENT_RE = re.compile(r"\b(?:disagree\w*|clash\w*|line up|agree|consistent|match|each record|all of them|say different|say so|as far as the records go)\b", re.IGNORECASE)

OWNER_NOTE = "Who owns a piece of work changes only where a note puts someone in charge of it: it was handed or passed to someone, someone took it over or picked it up, someone is the owner now in place of another. A person a later note gives the next step, a task or the ball, and a firm the work moved to as its vendor or supplier, are not thereby its owner; the owner is the person named in the last such note, and stays its owner even when the work was later cancelled, dropped or finished: a status or a firm is never the answer to who owns it."
PIT_ADDRESS_RE = re.compile(r"\baddress that was current\b", re.IGNORECASE)
TOPIC_NO_RECORD = "If the notes do not state it, say so."
CONTACT_NO_RECORD = "If the notes do not state it, say plainly that you have no record of it, and say which notes you did check by naming who or what each one is about — not by its label, and without repeating their contents or figures."
PIT_ADDRESS_NOTE = "The address this message asks about is the work email it names: give the work email the records held on that day as the answer, and do not say that you have no record of an address."
CONTACT_NOTE = "A person's current work email, which is what these notes mean by their work address, is the one the notes give for the employer they are at now; an address from before they moved is out of date."
NEXT_NOTE = "The next step is the one set by the latest note that gives the work a next action — a follow-up, or a handover with the new owner's first action. Give only that one step: on the ANSWER line, the person, then the task, then the channel, separated by ' ; ', each as short as the note puts it: the task without when or why, the channel alone, such as email, phone, chat or in person. Within one note, the passage that comes later holds; a later follow-up replaces the next action that came with a handover, and whoever owns the work is not always the one with the next step."
NEXT_PICK_NOTE = "Where a passage is picked out below as the most recent one about the work that gives a next action to a person, that passage holds the step to give unless a later passage about the work sets another: take the person, the task and the channel from it. An earlier passage does not outrank it, even one worded like the message, such as one naming the open action or the next step. Write the channel as the usual word for it, email, phone, chat or in person, even where the passage misspells it."
DISAGREE_NOTE = "Where it stands now is what the two latest notes about it say. When they give it different states, neither replaces the other: give both, and say that the records disagree. States from earlier notes, and its people, figures and vendors, are not what is asked."


HANDLE_NOTE = "A messaging handle the user later asked you to remove, or said they no longer use, is no longer on record: do not give it anywhere in the reply; say that you no longer have a handle for them on record, and say what the notes still hold about the person, such as their employer, role, city or work email. A handle the notes never withdrew is still on record: give it."
LEG_NOTE = "Before giving a number of days for one country on a trip, check that the notes put that country in that trip: its countries are the ones the note naming the trip lists, and a note that speaks of a trip only through the person it was planned with belongs to the trip planned with that same person, so days that a plan made with someone else gives for a country are not days of this trip. If the notes do not put the country in the trip, say that you have no record of time there, give no number of days, and name the countries the trip did include."
CHANGED_STAY_NOTE = "This asks about one stay of a trip: the stay that a later update to that trip changed. Find the update that changed one stay of this trip; it may name the trip only by the person it was planned with. The stay it names is the one asked about. Then give how many days the plan the message asks about gave that one stay: a single count of days, not the trip's total and not the other stays."
WHOLE_TRIP_NOTE = "When the message asks how long the whole trip is now, the total is the one thing it asks for, even where it also asks you to piece the stays together: work the stays out before you reply and leave them out of the reply; if you do mention them, write them as one plain sentence, not as a list. Reply with one sentence giving the total, then the line 'ANSWER: <total> days'."
SEVERAL_ON_ONE_LINE = 'when several things were asked, put them on that line in the order asked, separated by " and "'
TOTAL_ALONE = "when the message asks for a total, that line holds the total alone"
DIRECTION_LINE = 'when the message asks whether something raised, lowered or left a figure unchanged and what that figure now is, that line holds both: first raised, lowered or unchanged, then the figure, separated by " and "'
SEVERAL_SEMI = "when several things are asked, give them on that line in the order asked, separated by ' ; '."
BOTH_STATES = "when the message asks whether the notes agree on where it stands, even where it asks for each record or all of them, that line holds three things in this order, separated by ' ; ': the state one of the two latest notes gives the work, the state the other one gives it, and the word disagree. Each state is the word or two that note uses for what happened to the work, each word spelled correctly even where the note misspells it, without any hedge or remark the note adds to it."
NEXT_STEP_LINE = "when the message asks for the next step, that line holds three parts in this order, separated by ' ; ': the person who has it, the task, and the channel, all three even where the message names only some of them: the task in the note's words with each ordinary word spelled correctly even where the note misspells it, and the channel alone, such as email, phone, chat or in person, with no time or condition."
NO_RECORD_LEAD = "If none of the records states what was asked, "
LEG_NO_RECORD = "If none of the records states what was asked — and none does when the records do not put the country asked about in that trip, whatever days they give its other countries — say plainly that you have no record of time there, give no number of days for it, not even zero, and name the countries the trip did include"
PARTIAL_NO_RECORD = "If none of the records states what was asked — and none does when the records say a payment was made but not how much — say plainly that you have no record of how much was paid, so the balance does not follow, and say what the payment record itself says about that amount, in its own words, giving no figure from any record"
PARTIAL_PAYMENT_NOTE = "A balance left after a partial payment follows only when the notes give the amount that was paid. If they say a payment was made but not how much, say that you have no record of how much was paid, so the balance does not follow, and say what the payment record itself says about that amount, giving no figure. When the notes do give the amount paid, compute the balance."

SEQUENCE_NOTE = "This asks for the {kind} the work started with and then the one that replaced it or took over from it, in that order, each by its own name as the notes give it; the people who own or run the work are not what is asked."

PAYING_PARTY_NOTE = "In these records the commissioning party, client or paying customer is the organisation that pays us for the work; the supplier or vendor is the organisation we pay, the one billing us. Find the field the batch defines for the party that pays us, and answer with its value, the organisation's name, not the field's label."

FIGURE_NOTE = "The figure asked for is a count or an amount, how many days, nights, seats or percent or how much money, even where the message asks what the days or nights are now: never a date or a day of the week. It starts as the figure the work was first quoted or booked at, and only a note that changes that figure itself changes it: a correction that says what the count is now replaces it; a version that adds a number of the same unit to it, or takes a number of the same unit off it, changes it by exactly that number, so 5 percent taken off 40 percent leaves 35 percent. A delay, such as the schedule slipping by some days or weeks, moves when the work happens and leaves the figure as it was. When an approval comes with a cap, ceiling or envelope and the notes say how much of it has already gone out, is spoken for or is committed, the money figure asked for is what is left of it, the part still open: the cap less that amount, even where the message calls it a total. Compute the figure with the calculate tool and give that one figure on the ANSWER line, written as the notes write figures of its kind: with the unit word they use, and an amount of money to the cent; the reply names no other figure."
LESSON_NOTE = "The lesson is the saying the user wrote down as what they took from it or will remember next time, often a proverb, whatever the message calls it: what they learned, kept, resolved or will remember, a rule or a moral; a remark about where the note is filed or which note to read first is not the lesson, and nor is a step, a status or a person. Give the saying in their words."
WORDS_AS_WRITTEN = "When you write a value into your reply, use the record's or the message's own words for it, not joined or tidied; where a note misspells an ordinary word, write that word spelled correctly, while names, codes and addresses stay exactly as written."
STATUS_NOTE = "This asks what state it is in now, not who has it: give the status the latest note about where it stands gives it, in the word or words it uses for the state. Where that note gives a state more than once, the passage that comes later holds. A remark it adds after the state, such as what it still waits on, what is left over or how the user feels about it, neither changes nor takes back the state. Spell the state correctly even where the note misspells it: a word that is not English, or one that makes no sense for where work stands, is a slip for the state word it nearly matches."


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


def asks_leg(message: str) -> bool:
    return bool(LEG_RE.search(message)) and not asks_whole_trip(message)


def asks_changed_stay(message: str) -> bool:
    return all(rule.search(message) for rule in (STAY_RE, REVISED_RE, FIRST_PLAN_RE, DAYS_ASKED_RE)) and not NOW_RE.search(message) and not asks_whole_trip(message) and not LONGEST_RE.search(message)


def answer_line(system: str, message: str) -> str:
    if asks_whole_trip(message):
        return system.replace(SEVERAL_ON_ONE_LINE, TOTAL_ALONE, 1)
    if DIRECTION_RE.search(message):
        return system.replace(SEVERAL_ON_ONE_LINE, DIRECTION_LINE, 1)
    return system


def topic_answer_line(system: str, message: str) -> str:
    guide = read(message)
    if guide.asks_disagreement:
        return system.replace(SEVERAL_SEMI, BOTH_STATES, 1)
    if guide.asks_next_step:
        return system.replace(SEVERAL_SEMI, NEXT_STEP_LINE, 1)
    return system


def no_record_clause(message: str) -> str:
    if asks_leg(message):
        return LEG_NO_RECORD
    return PARTIAL_NO_RECORD if PARTIAL_PAYMENT_RE.search(message) else ""


def record_notes(message: str) -> list[str]:
    out: list[str] = []
    if HANDLE_RE.search(message):
        out.append(HANDLE_NOTE)
    if asks_whole_trip(message):
        out.append(WHOLE_TRIP_NOTE)
    elif asks_leg(message):
        out.append(LEG_NOTE)
    elif asks_changed_stay(message):
        out.append(CHANGED_STAY_NOTE)
    if PARTIAL_PAYMENT_RE.search(message):
        out.append(PARTIAL_PAYMENT_NOTE)
    if PIT_ADDRESS_RE.search(message) and EMAIL_RE.search(message):
        out.append(PIT_ADDRESS_NOTE)
    return out + ([DATED_NOTE] if DATED_RE.search(message) else [])


def program_notes(message: str) -> list[str]:
    return [PAYING_PARTY_NOTE] if PAYING_PARTY_RE.search(message) else []


def latest_notes(message: str) -> list[str]:
    guide = read(message)
    if guide.asks_disagreement:
        return [DISAGREE_NOTE]
    if guide.asks_lesson:
        return [LESSON_NOTE]
    return [NEXT_NOTE, WORDS_AS_WRITTEN] if guide.asks_next_step else [STATUS_NOTE, WORDS_AS_WRITTEN] if guide.asks_status else []


def words_rule(verbatim: str, message: str) -> str:
    guide = read(message)
    return WORDS_AS_WRITTEN if guide.asks_next_step or guide.asks_status else verbatim


def topic_decline(system: str, message: str) -> str:
    return system.replace(TOPIC_NO_RECORD, CONTACT_NO_RECORD, 1) if CONTACT_RE.search(message) else system


def sequence_note(message: str) -> str:
    kind = SEQUENCE_KIND_RE.search(message)
    if not SEQUENCE_RE.search(message) or kind is None:
        return ""
    noun = kind.group(1).lower()
    return SEQUENCE_NOTE.format(kind="moving company" if noun.startswith("moving") else noun)


def notes(message: str) -> list[str]:
    guide = read(message)
    out: list[str] = []
    if guide.asks_holder:
        out.append(OWNER_NOTE)
    if guide.asks_contact:
        out.append(CONTACT_NOTE)
    if guide.asks_next_step:
        out.append(NEXT_NOTE)
        out.append(NEXT_PICK_NOTE)
    if guide.asks_disagreement:
        out.append(DISAGREE_NOTE)
    if guide.asks_figure:
        out.append(FIGURE_NOTE)
    if guide.asks_lesson:
        out.append(LESSON_NOTE)
    if guide.asks_status:
        out.append(STATUS_NOTE)
    if sequence := sequence_note(message):
        out.append(sequence)
    return out


EMAIL_NO_RECORD = "If none of the records states what was asked — and none does when no record gives an email address for the person the message asks about, under their full name or a nickname the records give them — say plainly that you have no record of an email for them; then say whom the records do hold that the message's words point to — the person it calls by a nickname, anyone the records give the same first name, and the people at the employer or event it names — each by full name together with the nickname the records give them, and who they are by the records: their role, employer and city, never their email address. Write no one's email address anywhere in the reply, not in an offer to write to someone and not in the answer line"

UNNAMED_NO_RECORD = "If none of the records states what was asked — and none does when no stored conversation names the person the message asks about — say plainly that you have no record of that person, and name every person the note before the message names, each by full name with the nickname the records give them, as the ones the stored conversations do hold. Write no one's email address anywhere in the reply, not in an offer to write to someone and not in the answer line"

DATED_RE = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b")
DATED_NOTE = "This message asks what the records held on a past date. Go by the date each record was saved, not by how its words speak of time: what they held on that date about the person or thing asked about is what the last record about that same person or thing, saved on or before it, says, even where its words call it an old or earlier one and even where a record saved later replaced it; a record saved after that date was not there yet, and a record about someone or something else is not the answer, whatever its date."
