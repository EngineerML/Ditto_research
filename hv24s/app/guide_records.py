from __future__ import annotations

import re
from dataclasses import dataclass

from .guide_spelling import fold, read_form
from .memory.people import by_date, full_names, known_aliases
from .protocol import MemoryPair

NEXT_STEP_RE = re.compile(r"\bnext\b[^?.]{0,40}\b(?:step|move|action)\b|\b(?:open|pending) action\b|\bowes? the next\b|\bhas the ball\b|\bmeant to act next\b|\bwhat comes next\b|\bwaiting to happen\b|\bdoing what next\b|\bwho is doing what\b", re.IGNORECASE)
CONTACT_RE = re.compile(r"\b(?:e-?mail|work address|mail address)\b", re.IGNORECASE)
HOLDER_RE = re.compile(r"\b(?:owns?|owned|owner|running|runs|run it|holding|holds|has it|has the thread|accountable|responsible|on point|chase|in charge|whose is it)\b", re.IGNORECASE)
WHO_RE = re.compile(r"\b(?:who|whose|whoever|person|whom)\b", re.IGNORECASE)
STANDING_RE = re.compile(r"\b(?:where are we|stand|stands|state|status|position|landed|land|standing)\b", re.IGNORECASE)
FIGURE_RE = re.compile(r"\b(?:figure|total|how many|number|amount|work out|money|percent|seats|days|nights|hours|guests|items|units)\b", re.IGNORECASE)
CHANGED_RE = re.compile(r"\b(?:now|after|change\w*|adjust\w*|apply|follow\w*|final|arriv\w*|result\w*|land\w*|work out|come to)\b", re.IGNORECASE)
LESSON_RE = re.compile(r"\b(?:take away|took away|takeaway|lesson|remember next time|rule did i set|set myself|teach\w*|resolve\w* to do|do differently|advice i ke\w+|kept from it|keep from it|learn\w*|moral|stuck with me|stuck \w+ me at the end)\b", re.IGNORECASE)
ENDED_RE = re.compile(r"\b(?:end up|ended up|where it is|state of play)\b", re.IGNORECASE)
OPENING_QUESTION_RE = re.compile(r"^\s*where are we with [^?]*\?\s*(?:the [^.?]* one\.)?", re.IGNORECASE)
HANDLE_RE = re.compile(r"\b(?:signal|whatsapp|telegram|messaging)\b.{0,120}\bhandle\b|\bhandle\b.{0,40}\b(?:signal|whatsapp|telegram)\b", re.IGNORECASE | re.DOTALL)
LEG_RE = re.compile(r"\bhow many days did we spend in\b|\bhow long was the [^?]{1,40} stay\b|\bhad us in\b|\bhow many days are we spending (?:in|there)\b|\bhow many days does [^?]{1,80} give us in\b", re.IGNORECASE)
LONGEST_RE = re.compile(r"\blongest\b", re.IGNORECASE)
WHOLE_TRIP_RE = re.compile(r"\bwhole trip\b|\baltogether\b|\bfull length\b|\bin total\b|\bhow many days is (?!the changed)|\bhow long [^?]{0,60} is now\b", re.IGNORECASE)
TRIP_RE = re.compile(r"\b(?:trip|legs|stays)\b", re.IGNORECASE)
PAYING_PARTY_RE = re.compile(r"\b(?:commission\w*|paying customer|pays us|the one we pay|supplier we pay|billing us|our client|our supplier)\b", re.IGNORECASE)
PARTIAL_PAYMENT_RE = re.compile(r"\bpartial payment\b", re.IGNORECASE)
DIRECTION_RE = re.compile(r"\braise\w*\b[^?]{0,40}\blower\w*\b|\bincrease\w*\b[^?]{0,40}\bdecrease\w*\b|\bgo up\b[^?]{0,30}\bgo down\b", re.IGNORECASE)
AGREEMENT_RE = re.compile(r"\b(?:disagree\w*|clash\w*|line up|agree|consistent|match|each record|all of them|say different|say so|as far as the records go)\b", re.IGNORECASE)

# A question asking for the next step in parts: who, what, and how or by what means.
PARTS_WHO_RE = re.compile(r"\b(?:who|whom|person|owner)\b", re.IGNORECASE)
PARTS_WHAT_RE = re.compile(r"\bwhat\b|\btask\b|\baction\b|\bstep\b|\bmove\b|\bdo\b", re.IGNORECASE)
PARTS_HOW_RE = re.compile(r"\bhow\b|\bmeans\b|\bchannel\b|\bthrough what\b|\bthe way\b|\bvia which\b|\bover which\b|\bin touch\b|\breach out\b", re.IGNORECASE)

OWNER_NOTE = "Who owns a piece of work changes only where a note puts someone in charge of it: it was handed or passed to someone, someone took it over or picked it up, someone is the owner now in place of another. In a handoff written as one name to another, the second name holds it now. A person a later note gives the next step, a task or the ball, and a firm the work moved to as its vendor or supplier, are not thereby its owner; the owner is the person named in the last such note, and stays its owner even when the work was later cancelled, dropped or finished: a status or a firm is never the answer to who owns it. The person to chase about a piece of work, or to ask about it, is its owner, not whoever has the next task."
CONTACT_NOTE = "A person's work address in these notes is their work email, and a request for it wants that email on the ANSWER line, not their name or role. A person's current work email is the one the notes give for the employer they are at now; an address from before they moved is out of date. A note can give someone's email under the nickname another note gives them, and that is still their email. Two people can share a nickname: the employer in a note or the name in the address says which of them it is about."
NEXT_NOTE = "The next step is the one set by the latest note that gives the work a next action — a follow-up, or a handover with the new owner's first action. Give only that one step: on the ANSWER line, the person, then the task, then the channel, separated by ' ; ', each as short as the note puts it: the task is the action the note gives that person to do (such as \"return the signed form\"), not the handover itself, and comes without when, why or any reference number; the channel alone, one word or two with nothing after it, such as email, phone, chat or in person (\"Ann Lee ; book the site visit ; phone\"). Write the task and the channel with every word spelled correctly, even where the note misspells it; names exactly as the notes give them. A note that the work was cancelled, paused or finished changes its state: a next action a note gave stands unless a note says it was dropped or done, so give it. Say there is no next step only where no note gives one. Within one note, the passage that comes later holds; a later follow-up replaces the next action that came with a handover, and whoever owns the work is not always the one with the next step. The task is the verb and what it acts on, without the thread's name: \"book the site visit\", not \"book the site visit for the kitchen job\"."
DISAGREE_NOTE = "This asks what state each record gives it. Read every passage that says where it stands or what state it is in, in all of the thread's notes, including notes saved at the same time and another person's version reported in them (\"the version from ...\"); a handover, a next step or who is waiting on whom is not a state. When they give different states, say that the records disagree. On the ANSWER line give the state from the user's own latest note about where it stands first, then the state the other version gives, each as the one or two status words the notes use for it (without qualifiers such as \"pending one signature\") and spelled correctly even where the note misspells it, then the single word disagree, separated by ' ; ': <state> ; <other state> ; disagree. When the states differ that line must end with that one word, disagree, and holds the two states and that word only, not an entry for each note, even when the message asks what each record says. When the notes agree, give the one state."


HANDLE_NOTE = "A messaging handle the user later asked you to remove, or said they no longer use, is no longer on record: do not write it anywhere in the reply, in any tense or form, not even to say what was removed; say that you no longer have a handle for them on record, and in the same reply name what the notes still hold about the person: the nickname the notes give them, their employer, their role and their city, in the notes' words. A handle the notes never withdrew is still on record: give it."
LEG_NOTE = "Before giving a number of days for one country on a trip, check that the notes put that country in that trip. If they do, give its days as usual. Only if they do not: say that you have no record of time there and name each country the trip did include and the person it was planned with, as the notes give them, with no number of days anywhere in the reply, on the one line: 'ANSWER: I have no record of time in <that country>; the trip went through <each country>, planned with <the person>'."
WHOLE_TRIP_NOTE = "When the message asks how long the whole trip is now, the total is the one thing it asks for, even where it also asks you to piece the stays together: work the stays out before you reply and leave them out of the reply entirely. The line is 'ANSWER: <total> days', with no country or stay on it."
SEVERAL_ON_ONE_LINE = 'when several things were asked, put them on that line in the order asked, separated by " and "'
TOTAL_ALONE = "when the message asks for a total, that line holds the total alone"
PARTIAL_PAYMENT_NOTE = "A balance left after a partial payment follows only when the notes give the amount that was paid. When they do, compute the balance. Only if they say a payment was made but not how much: say that you have no record of how much was paid, so the balance does not follow, and say where the notes say that amount is or will come from (such as a bank export not yet pasted), in their words, with no figure anywhere in the reply, not the approved total and not any other amount, on the one line: 'ANSWER: I have no record of how much was paid, so the balance does not follow; the amount is in <where the notes say it is>'."

DIRECTION_NOTE = "This asks two things: whether the change raised, lowered or left the figure unchanged, and the figure now. Give both, in that order, on the ANSWER line: the direction as one word (increase, decrease or unchanged), then ' ; ', then the resulting figure in the unit asked for: 'ANSWER: <increase, decrease or unchanged> ; <figure>'. The direction word is about the one item the message names, and the figure now is still worked out in full: when that item leaves it unchanged, every payment the note gives still comes off: a start of 100, an item that leaves it unchanged and 30 paid gives 'unchanged ; 70'."
ACTION_ASK_RE = re.compile(r"\bnext (?:action|step|move)\b|\b(?:settle|settled|decide|decided|agree|agreed) (?:on )?(?:doing|to do)\b|\bdoing about\b", re.IGNORECASE)
AFTER_CHANGE_RE = re.compile(r"\bafter (?:the|that|their|our|this) [^?.]{0,30}\b(?:change|update|switch|swap)\b", re.IGNORECASE)
AFTER_CHANGE_NOTE = "A question about what holds after a change asks for what holds now: apply that change and every note after it, not only that one change."
WHO_RUNS_RE = re.compile(r"\bwho (?:runs|is running)\b", re.IGNORECASE)
SAME_ROLE_NOTE = "Notes can name one role in different words: whoever runs something is also its organiser, so a note on who organises it is about the same role as a note on who runs it, and the later one holds."
ACTION_ALONE_NOTE = "An action on the ANSWER line is the verb and what it acts on, without when or why: \"cancel it\", not \"cancel it before the renewal\"."
PAYING_PARTY_NOTE = "In these records the commissioning party, client or paying customer is the organisation that pays us for the work; the supplier or vendor is the organisation we pay, the one billing us. Find the field the batch defines for the party that pays us, and answer with its value, the organisation's name, not the field's label."

FIGURE_NOTE = "When an approval, envelope or budget comes with a cap or total and the notes say how much of it is already committed, spent, gone out or spoken for, that is the change, and the money figure asked for is what is left open: the total less that amount, never the total itself. When a later note corrects a figure, the corrected one replaces the earlier one; when a note adds to or takes off a figure, apply that change to the figure it names, as a plain sum even in percent: 4 percent off 42 percent is 38 percent. A schedule that slipped or was pushed back by some days or weeks moves the dates, not the figure: leave it out of the sum. A note that the work was cancelled, dropped or put off does not change the figure: the sum stands. Compute the figure with the calculate tool and give that one figure on the ANSWER line."
LESSON_NOTE = "The lesson is the saying the user wrote down as what they took from it or will remember next time, often a proverb; a remark about where the note is filed or which note to read first is not the lesson. Whatever the message calls it (a lesson, a rule, what was resolved, what to do differently), that saying is the answer. Copy the saying word for word, on the ANSWER line too; do not restate it as something the user resolved to do."
STATUS_NOTE = "This asks what state it is in now, not who has it and not what is waiting to happen: give the state the latest note about where it stands gives the matter (a state such as delivered, completed, postponed, cancelled, on hold or in progress), as one status word or short phrase, spelled correctly even where the note misspells it. Give the state in the note's own words for it, without changing them into another state word, and leave off anything after them. Who is waiting on whom, a handover, a next action or a figure put right ('is corrected — the count is now 27') is not its state."


@dataclass(frozen=True)
class Guide:
    asks_next_step: bool
    asks_holder: bool
    asks_contact: bool
    asks_disagreement: bool
    asks_figure: bool
    asks_lesson: bool
    asks_status: bool


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
STATE_RE = re.compile(r"\b(?:started|underway|under way|kicked off|quoted|approved|signed off|green-lit|cleared|authori[sz]ed|on hold|paused|stalled|frozen|suspended|corrected|revised|amended|restated|in progress|in motion|being worked|in hand|moving|delivered|handed over|shipped|fulfilled|closed|wrapped up|finished|done|complete|completed|cancell?ed|called off|scrapped|dropped|abandoned|withdrawn|planned|pencill?ed in|sketched out|mapped out|booked|reserved|locked in|secured|confirmed|firmed up|nailed down|definite|set|postponed|pushed back|delayed|deferred|put off|rebooked|moved|rescheduled|switched over|re-arranged|disputed|contested|challenged|under query|in dispute|settled|resolved|sorted|squared away|agreed)\b", re.IGNORECASE)
# Sentences that use those words for a change of hands, firm or figure, or for what happens next, rather than for the state.
NOT_STATE_RE = re.compile(r"\b(?:went to|let us down|booked\b[^.;]{0,60}\bthrough|first (?:supplier|service|place|vendor|company|provider)|record was|having started|started at|that started|started with|on the condition|the cap\b|capped|dropped off|away from|moved from|in charge|from\b[^.;]{2,50}\bto\b|the count is now|is the owner|now owns|ownership|the ball is|is waiting on|is going to|agreed to|next step|next on|first action|open action|will \w+)\b", re.IGNORECASE)
UNCHANGED_LINE = "An item that leaves the figure unchanged adds nothing to it and takes nothing off it, and what was paid or used still comes off: a start of 100, an item that leaves it unchanged and 30 paid gives 'unchanged ; 70'."
RESULT_ONLY_LINE = "Reply with the ANSWER line alone, holding the result worked out in full from every item and payment the note gives, and no other figure."
REMAINING_NOTE = "What remains is worked out from the note about that account alone: its starting figure, then each item as that note says it counts on this account (added on top, deducted, or not affecting it at all), then what is already used, paid or taken, which always comes off what remains. An item the note says is added or goes on top raises what remains, also when the message only asks how many are left: a start of 100 with 10 added and 30 used leaves 80. The same kind of item can count differently on another account. If the note lacks a figure this needs, say so instead."
RECORDS_DIFFER_RE = re.compile(r"\baccording to each (?:record|note)\b|\beach (?:record|note) say|\b(?:two|the) \w+ say different\b|\btell me if the \w+ \w+\b", re.IGNORECASE)
DATED_STAY_NOTE = "Reply to a question about a stay on a given date with the number of days alone: do not write the date or any other figure in the reply."
ONE_VALUE_RE = re.compile(r"\bafter every \w+ \w+\b.{0,30}\b(?:who|which person|what contact)\b", re.IGNORECASE)
STAYS_TOTAL_RE = re.compile(r"\badd up the current \w+ of\b.{0,120}\bhow many \w+ in total\b", re.IGNORECASE | re.DOTALL)
ORDER_NOTE = "This asks for the firms the work has been with, in the order they came: each is a company named as its vendor, supplier, venue or the like. A person who owns or runs the thread is not one of them, and a handover to a person changes no firm."
ORDER_ASK_RE = re.compile(r"\boriginal (?:\w+ ){1,2}then current \w+\b|\bchanges, earliest first\b|\bin order for me\b|\bwho did we start with\b|\bwho took over\b|\bin what order did\b|\bsequence of \w+|\bcame first and which\b|\bin the order they came\b|\boldest to newest\b|\bwas original and which\b|\bhistory in order\b|\bthen second \w+", re.IGNORECASE)
EARLIER_EMAIL_RE = re.compile(r"\b(?:originally|pre-correction|prior to the (?:fix|correction)|before the (?:fix|correction))\b", re.IGNORECASE)
EARLIER_EMAILS_FIRST = "These are oldest first."


def without_opening_question(message: str) -> str:
    rest = OPENING_QUESTION_RE.sub("", message, count=1)
    return rest if rest.strip() else message


def read(message: str) -> Guide:
    # Misspelt cue words are read as the words they stand for (app/guide_spelling.py); only the choice of note changes.
    message = fold(read_form(message))
    next_step = bool(NEXT_STEP_RE.search(message)) or bool(PARTS_WHO_RE.search(message) and PARTS_WHAT_RE.search(message) and PARTS_HOW_RE.search(message) and not CONTACT_RE.search(message))
    holder = not next_step and bool(HOLDER_RE.search(message)) and (bool(WHO_RE.search(message)) or bool(CONTACT_RE.search(message)))
    contact = holder and bool(CONTACT_RE.search(message))
    disagreement = not next_step and not holder and (bool(RECORDS_DIFFER_RE.search(message)) or (bool(STANDING_RE.search(message)) and bool(AGREEMENT_RE.search(message))))
    asked = without_opening_question(message)
    # What is asked is in the last sentence: the ones before it name the thread, and a thread's name can read as a word for a figure.
    figure = not next_step and not holder and bool(FIGURE_RE.search(re.split(r"[.?!]\s+", message.strip())[-1])) and bool(CHANGED_RE.search(message))
    lesson = not next_step and not holder and bool(LESSON_RE.search(message))
    status = not next_step and not holder and not disagreement and not figure and not lesson and (bool(STANDING_RE.search(asked)) or bool(ENDED_RE.search(asked)))
    return Guide(next_step, holder, contact, disagreement, figure, lesson, status)


def story_step_question(message: str) -> bool:
    # Who has a thread's next step, who holds it now, or the order its vendors came in: asked of the thread's notes however
    # the sentence is built ("Spell out the next move for me"), so the routing of the sentence does not decide where it is read.
    guide = read(message)
    return guide.asks_next_step or guide.asks_holder or guide.asks_disagreement or bool(ORDER_ASK_RE.search(fold(read_form(message))))


def asks_order(message: str) -> bool:
    return bool(ORDER_ASK_RE.search(fold(read_form(message))))


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


def asks_one_value(message: str) -> bool:
    return bool(ONE_VALUE_RE.search(read_form(message)))


def asks_state_only(guide: "Guide") -> bool:
    return guide.asks_status and not (guide.asks_next_step or guide.asks_holder or guide.asks_disagreement or guide.asks_figure)


def asks_contact_detail(message: str) -> bool:
    return bool(CONTACT_DETAIL_RE.search(read_form(message)))


def asks_account_figure(message: str) -> bool:
    message = read_form(message)
    return bool(REMAINING_RE.search(message) or DIRECTION_RE.search(message))


def asks_stays_total(message: str) -> bool:
    return bool(STAYS_TOTAL_RE.search(read_form(message)))


def asks_handle(message: str) -> bool:
    return bool(HANDLE_RE.search(fold(read_form(message))))


def asks_whole_trip(message: str) -> bool:
    return bool(STAYS_TOTAL_RE.search(message)) or bool(TRIP_RE.search(message)) and bool(WHOLE_TRIP_RE.search(message)) and not LONGEST_RE.search(message)


def answer_line(system: str, message: str) -> str:
    return system.replace(SEVERAL_ON_ONE_LINE, TOTAL_ALONE, 1) if asks_whole_trip(message) else system


def record_notes(message: str) -> list[str]:
    message = fold(read_form(message))
    out: list[str] = []
    if HANDLE_RE.search(message):
        out.append(HANDLE_NOTE)
    if asks_whole_trip(message):
        out.append(WHOLE_TRIP_NOTE)
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


def closing_line(message: str) -> str:
    read = fold(read_form(message))
    if not REMAINING_RE.search(read):
        return ""
    return f"{RESULT_ONLY_LINE} {UNCHANGED_LINE}" if DIRECTION_RE.search(read) else RESULT_ONLY_LINE


def program_notes(message: str) -> list[str]:
    out = [PAYING_PARTY_NOTE] if PAYING_PARTY_RE.search(message) else []
    if ACTION_ASK_RE.search(fold(read_form(message))):
        out.append(ACTION_ALONE_NOTE)
    if AFTER_CHANGE_RE.search(fold(read_form(message))):
        out.append(AFTER_CHANGE_NOTE)
    return out


def notes(message: str) -> list[str]:
    guide = read(message)
    out: list[str] = []
    if ORDER_ASK_RE.search(fold(read_form(message))):
        out.append(ORDER_NOTE)
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


# The user's short notes about the trip a question about one country's stay names, shown beside the records: the countries a trip went
# through and who planned it are the ground for saying a country was not part of it.
TRIP_NOTES_HEADER = "The user's short notes that name this trip:"
TRIP_NOTE_CHARS = 400
NAME_STOP = frozenset("""a an and the our we us i my me you your of on in at to for from with by after before about this that
these those how many much long did do does was were is are be been had have has days day nights stay stays spend spent
spending trip trips last next year move break summer spring autumn winter fall there here now changed change updated
update remind which what when where""".split())


def trip_notes(message: str, pairs: list) -> list:
    if not LEG_RE.search(fold(read_form(message))) or asks_whole_trip(fold(read_form(message))):
        return []
    words = re.findall(r"[A-Za-z]+", message.lower())
    names = {f"{a} {b}" for a, b in zip(words, words[1:]) if a not in NAME_STOP and b not in NAME_STOP}
    found = [pair for pair in pairs if len(pair.prompt) < TRIP_NOTE_CHARS and "trip" in pair.prompt.lower() and any(re.search(r"\b" + re.escape(name) + r"\b", pair.prompt.lower()) for name in names)]
    return sorted(found, key=lambda pair: (pair.timestamp, pair.pair_id))[:6]
