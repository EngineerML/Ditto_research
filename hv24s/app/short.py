from __future__ import annotations

import asyncio
import difflib
import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .action import OPERATOR_SEAM, VALUE_VERBATIM, Outcome, TokenTally
from . import guide_records
from .english_words import WORDS
from .guide_spelling import LOOKALIKES, SHORT_WORDS, STATE_WORDS, SpellingKey, fold, read_form, read_slips
from .answer import parse_slot
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, asked_part, identifier_tokens, tokens
from .memory.people import ALIAS_RE, FULL_NAME_RE, ORDINARY_OPENERS, SHORT_RECORD_CHARS, alias_lines, by_date, cards_for, full_names, known_aliases, no_email_held, person_card
from .memory.topic import Topic, TopicIndex, paragraphs, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_ANSWER_LINE = "Reply briefly, with no figure or date the message did not ask for, not even those the answer was worked out from, and with any money figure to its two decimal places, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
PROGRAM_SYSTEM = f"{SHORT_OPENING} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year, even when the message asks for less. If the notes do not state it, say so."
INNER_NAME_RE = re.compile(r"(?<=[a-z,] )([A-Z][a-z]{2,})\b")
EVENT_ID_RE = re.compile(r"\b[a-z]+-[0-9a-f]{8,}\b")
ROW_NOT_VALUES = frozenset({"assign"})
QUOTED_VALUE_RE = re.compile(r'"([^"]+)"')
ROW_PREFIX_RE = re.compile(r"^\[[^\]]*\][^:]*:\s*")
ROW_FIGURE_RE = re.compile(r"\b\d+\b")
ROW_CHANGE_RE = re.compile(r"\b(?:add|remove)\b")
CODE_TAG_RE = re.compile(r"</?code>")
CELLS_RE = re.compile(r"^\||^[^ ,]+,")
TABLE_RULE = frozenset("|-: ")
EVENT_SHOWN = "From the user's case file, by code: its opening line, then every line of it that names {start} or an id linked to it, copied as written and in the file's own order; not checked. These are all the lines of this file on those ids, so no search for more of them is needed:"
ONE_LINE_ANSWER = "Reply with one line only, beginning 'ANSWER: ', with only the value asked for, as short as the notes put it, in their words; when several things are asked, give them on that line in the order asked, separated by ' ; '. Do all your working before you reply and write none of it: no figure or date the message did not ask for, not even those the answer was worked out from, and any money figure to its two decimal places."
NOT_STATED_LINE = "If the notes do not state something asked, say so on that line, with what they do hold on it."
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {ONE_LINE_ANSWER} Write any date in full, with day, month and year. A thread that was finished, dropped or cancelled still has the last person who held it and the last next action a note gave. {NOT_STATED_LINE}"
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MIN_SECONDS = 8.0
READINGS_HELD = 512
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
LEAD_MAX_STATEMENT_CHARS = 1000
PROGRAM_MAX_RECORD_CHARS = 2000
PERSON_BRIEF = "Before the message is answered: which person is it asking about? Reply with that person's full name as the notes give it, and nothing else."
RECENT_HEADER = "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:"
RECENT_LINE = "- The most recent passage about “{phrase}”: {passage}"
RECENT_HANDOVER_LINE = "- The most recent passage about “{phrase}” that puts a person in charge of it: {passage}"
HANDOVER_RE = re.compile(r"\b(?:handed (?:over )?to|handed \w+ (?:\w+ )?to|passed [^.;]{0,40}\bto\b|picked up [^.;]{0,40}\bf[a-z]{1,3}m\b|is the owner|owner now|now owns|ownership of|'s now|in charge|to run\b|holding the thread|the handoff|run point|took it on|the one accountable|owning|a name on it)", re.IGNORECASE)
RECENT_ACTION_LINE = "- The most recent passage about “{phrase}” that gives a next action to a person: {passage}"
ACTION_CUE_RE = re.compile(r"\b(?:next \w{2,5} is now|next step|next move|next from them|first action from|follow-up for|open action|one action|action on [^.:]* is with|is waiting on|the ball is with|agreed to|is going to|will \w+|would \w+|next on)\b", re.IGNORECASE)
HANDOVER_SLIPS = frozenset({"handed", "passed", "picked"})
HANDOVER_CUE_WORDS = frozenset("handed passed picked owner owns ownership charge handoff point accountable owning took".split())
RECEIPT_NOTE_RE = re.compile(r"\b(?:receipt|scratch note)\b|can be deleted once", re.IGNORECASE)
RECEIPT_HEADER = "The note about this person that calls itself a receipt or scratch note, found by code, with the id a call needs; not checked:"
RECIPIENT_NOTE_RE = re.compile(r"\b(?:go|goes) to\b|\bwho\b", re.IGNORECASE)
RECIPIENT_NOTE_CHARS = 500
RECIPIENT_HEADER = "The user's note on who this project's numbers or update go to, found by code from the project's name; not checked:"
SCRATCHPAD_HEADER = "The note that calls itself the scratchpad of the project this message names, found by code from the project's name; not checked:"
STATES_DIFFER_LINE = "If these sentences give two different states, end with the line 'ANSWER: <the user's own latest state> ; <the state the other version gives> ; disagree', each state in the words the sentence uses, spelled correctly; if they agree, give the one state."
DRAFT_PASSAGES_HEADER = "From the user's saved notes on this thread, picked out by code from the dates of the notes and the order of the passages in them; not checked:"
STEP_PASSAGES_HEADER = "Picked out by code from the dates of the notes and the order of the passages in them, as a place to start; not checked — the notes above decide wherever they differ:"
RECENT_STATE_LINE = "- The most recent sentence about “{phrase}” that gives its state: {passage}"
RECENT_STATES_LINE = "- A sentence about “{phrase}” that gives a state (oldest first): {passage}"
SENTENCE_END = re.compile(r"(?<=[.!?;])\s+|\n+")
NAMELESS_ACTION_RE = re.compile(r"\b(?:them|they|their)\b", re.IGNORECASE)
SAME_QUESTION_RATIO = 0.9
OPEN_AMOUNT_LINE = "Where a passage gives a total and how much of it is committed, spent or spoken for, the money figure is what is left open: the total less that amount."
COMMITTED_RE = re.compile(r"\b(?:committed|spoken for|gone out|already spent|has gone)\b", re.IGNORECASE)
NEXT_TASK_LINE = "The task on the ANSWER line is the verb and what it acts on, without the thread's name."
PASSAGE_CARDS_HEADER = "The user's short notes on the people that passage names, under every name they go by, found by code; not checked:"
SCHEDULE_SLIP_RE = re.compile(r"\b(?:schedule|timeline|date|deadline|start)\b[^.;]{0,30}\b(?:slipped|slid|moved|pushed|delayed)\b|\b(?:slipped|pushed back|delayed) by\b", re.IGNORECASE)
PASSAGE_ONE_ASK = "An opening such as \"where are we with it\" only names the thread: what is asked is what the message goes on to ask, and that is all the ANSWER line holds."
RECENT_LESSON_LINE = "- The most recent sentence about “{phrase}” that gives what the user took from it: {passage}"
LESSON_SENTENCE_RE = re.compile(r"\b(?:lesson|took from it|rule for next time|stuck with me|note afterwards|one line on a|takeaway)\b", re.IGNORECASE)
LESSON_NOT_RE = re.compile(r"\b(?:read first|filed under)\b", re.IGNORECASE)
RECENT_FIGURE_LINE = "- A sentence giving a figure (oldest first): {passage}"
REFERENCE_RE = re.compile(r"\b(?:[A-Z]{1,5}[-/]?\d[\w/-]*|[A-Z]+-[A-Z0-9]+)\b")
REFERENCE_WORDS_RE = re.compile(r"\b(?:ticket|booking reference|purchase order|file number|job number|case CASE|reference)\b", re.IGNORECASE)
THREAD_FIGURE_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
FIGURE_WORDS_RE = re.compile(r"\b(?:cap|ceiling|envelope|committed|total|count|quoted|version|nights|days|seats|hours|percent)\b|\$\d", re.IGNORECASE)
RECENT_REPLACED_LINE = "- An earlier next action, replaced by the one on the next line (also when both are in one note or carry the same date): {passage}"
ACTION_CUE_WORDS = frozenset("next step move first one action follow waiting ball agreed going will would".split())
ACTION_CUE_LOOKALIKES = LOOKALIKES | frozenset("well wall wild wile kill mill fill bill nest text gong wound fist".split())
RECENT_PERSON_LINE = "- The most recent passage about “{phrase}” that names a person: {passage}"
RECUR_SHARE = 0.8
RECUR_EXTRA_WORDS = 6
RECUR_TIMES = 2
RECUR_MAX_WORDS = 40
RECUR_TYPO_WORD = 4
LATEST_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
LATEST_BRIEF = "Passages:\n{passages}\n\nMessage:\n{message}"
SHARED_DRAFT_NOTE = "A draft reply, written once from these same notes for the question \"{asked}\"; it has not been checked, and the notes decide wherever they differ:\n{draft}\n\nCheck the draft against the notes, then reply to the message as asked at the start. The same question asked in other words gets this same draft: where the notes bear the draft's answer out, keep that answer in the same words, so the same question always gets the same answer; change it only where a note shows it is wrong."
DRAFT_CHECK_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the user's saved notes on one thread, the passage picked out of them, a message, and the reply you drafted to it from that passage. Keep to your draft: unless the notes plainly show it wrong, send it again word for word, ending with its ANSWER line. Only a passage later than the picked one, saying something else about the very thing asked, shows it wrong: an earlier passage, a passage about something else or one that says less does not. If you find one, quote it word for word with its mark and date, say what it changes, and end with one line 'ANSWER: <the value asked for>'. If you cannot quote one, send the draft again word for word. Do not mention the draft."
DRAFT_CHECK_BRIEF = "{notes}\n\nMessage:\n{message}\n\nYour draft reply:\n{draft}"
DRAFT_STATES_DIFFER = "This message asks whether the records differ: passages that give different states are what a draft reports, not a reason to change it. When they differ the reply ends with the line 'ANSWER: <the user's own latest state> ; <the state the other version gives> ; disagree', never one state or that word alone."
DRAFT_NOT_THE_OWNER = "Someone a later passage gives a task, or says is being waited on, is not thereby who holds it, and someone reporting a version (“Pat has it down as canceled”) does not hold it. A passage naming a company or vendor that took over the supply names a supplier, not who owns the work, so it cannot show this draft wrong: only a later passage that puts another person in charge shows the draft wrong."
DRAFT_NEXT_STANDS = "A passage saying the work is finished, firmed up, deferred, paused, dropped or cancelled names a state, not a person or a task, so it cannot show this draft wrong: the next action a note gave stands, and only a later passage that gives another person or another task to do shows the draft wrong."
SAME_FILE_SHARE = 0.99
SAME_FACTS_LINE = "Code found the same values on the lines of the two case files for these ids, so the two file codes hold the same facts here (a comparison of the values on each line, not a reading of them, and not checked)."
SAME_WORDS_LINE = "Code found the same words and figures in the notes filed under the two file codes, so they may hold the same facts here (a comparison of words, not a reading of them, and not checked)."
SAME_QUESTION_BRIEF = "The earlier question:\n{question}\n\nYour reply to it:\n{reply}\n\nNew message:\n{message}"
SAME_QUESTION_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are a question about one of the user's case files, the reply you gave to it, and a new message that code matched to that question over the same notes; code may be wrong. Different opening or closing words about how to read the file, a different case file code holding the same facts, a different way of asking for the answer and slips of the keyboard do not make it another question. Keep to your reply and do not work the answer out again: if the new message asks for the same thing, send your reply again, word for word, ending with its ANSWER line. Only if the new message asks for something else, reply with only the word DIFFERENT."
SAME_QUESTION_NO = "DIFFERENT"
SAME_QUESTION_MAX_TOKENS = 600
SAME_QUESTION_TRIES = 2
SHARED_WAIT_RESERVE = 60.0
ASIDE_RE = re.compile(r"^(?:separately|unrelated)\b", re.IGNORECASE)
# Filed order: Bench 14 files a case file's notes in the order things were said, so
# a program question reads them in that order, each with its full filing time, and the model follows them one by one.
FILED_PROGRAM_SYSTEM = PROGRAM_SYSTEM.replace("Write any date in full, with day, month and year, even when the message asks for less.", "Use the date precision the user requests; otherwise give the full date when the notes establish it.", 1)
FILED_ORDER_HEADER = "The statements of the notes below, in the order they were saved, oldest first:"
FILED_ORDER_NOTE = "The notes are dated by when they were saved, and a later note comes after an earlier one. A later note can change a value, or take a change back: a note that reverts, goes back or returns to the previous entry or arrangement undoes the change made just before it, so the value is again the one that held before that change (entries A, then B, then C, then \"back to the previous arrangement\": the value is B, not C), even when the change it undoes called itself the newest or the one that governs. A later note can say that an earlier entry was a mistake, was logged in error or has been struck (it never took effect, so the value before it still stands), or record a proposal that was declined or not adopted (nothing changes). A note that calls itself the newest or the one that governs is still only one note in that order, and later notes can undo it. When the message asks for a list, start from the list a note gives and apply every later note that adds, removes, swaps or puts back an item. Follow the notes in that order and give the value that holds at the time the message asks about: now, unless the message names another time. The ANSWER line gives only that value, never an earlier one beside it."
NAME_THE_NOTES = "name the note that says which thing the message asks about (where the notes define their own labels, the note defining the label whose meaning fits the question, counting anything the question rules out), then the note that gives its value; then name, by their marks only and without writing any of their values, the notes that set, change, take back or cancel that value, in the order they were saved"
DRAFT_STEPS = f"Before the ANSWER line, {NAME_THE_NOTES}."
ONE_VALUE_STEP = "This message asks for one person or contact: the one holding it after the last reassignment. The ANSWER line holds that one value alone, with no ';' in it."
DECIDE_STEPS = f"Before your ANSWER line, {NAME_THE_NOTES}. The ANSWER line then gives what the last of those notes leaves standing, with no value from an earlier note it replaced, unless the message asks for a list."
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


def record_size(pair: MemoryPair) -> int:
    return len(pair.response) + len(pair.prompt)


def short_records(focus: list[Candidate], max_chars: int) -> bool:
    return sum(record_size(cand.pair) for cand in focus) <= max_chars and all(record_size(cand.pair) <= PROGRAM_MAX_RECORD_CHARS for cand in focus)


def focus_token(message: str, focus: list[Candidate]) -> str:
    for token in identifier_tokens(message):
        if focus and all(token in (cand.pair.prompt + " " + cand.pair.response).lower() for cand in focus):
            return token
    return ""


def statement(pair: MemoryPair, token: str) -> str:
    text = pair.prompt
    at = text.lower().find(token)
    body = text[at + len(token):] if at >= 0 else text
    return SPACE.sub(" ", body).strip(EDGE)


def record_block(mark: int, pair: MemoryPair) -> str:
    head = f"[M{mark}] {pair.timestamp[:10]}" if pair.timestamp else f"[M{mark}]"
    return f"{head}\nUser: {pair.prompt}\nAssistant: {pair.response}"


def undated_block(mark: int, pair: MemoryPair) -> str:
    return f"[M{mark}]\nUser: {pair.prompt}\nAssistant: {pair.response}"


# Revert reading (filed order only; a case-file currency note): an entry that says it goes back to the previous entry
# or arrangement takes back the change made by the entry just before it about the same thing (two content words in
# common, asides left out), so the value is again the one the entry before that gave. Read from wording alone and shown
# to the deciding model as unchecked; the notes decide.
REVERT_RE = re.compile(r"\b(?:revert\w*|returned to the previous|returns to the previous|back to the previous|went back to the|goes back to the|undo(?:es|ne)? the last)\b", re.IGNORECASE)
REVERT_STOP = frozenset("the and for from now that this with was were has have had are its it's into onto than then there their them they our out per any all one two also just only instead entry previous newest governs logged change update".split())
REVERT_HEADER = "Read by code from the wording of the entries below (not checked; the notes decide wherever they differ):"
DECLINED_RE = re.compile(r"\b(?:request|proposal|suggestion|draft)\b[^.]{0,120}\b(?:was|were|got)\s+(?:dropped|turned down|declined|rejected|withdrawn)\b", re.IGNORECASE)
IN_ERROR_RE = re.compile(r"\b(?:logged|entered|recorded|filed|noted|saved) (?:in error|by mistake)\b|\bnever took effect\b|\bwas a mistake\b", re.IGNORECASE)
IN_ERROR_LINE = "- M{at} says an earlier entry was logged in error and never took effect: that is M{undone}, the change before it about the same thing, even where the two write the value differently (5:20 pm and 17:20 are one time), so the value stays the one M{restored} gives."
DECLINED_LINE = "- M{at} says the change proposed in M{undone} did not go ahead, so the value stays the one M{restored} gives."
REVERT_LINE = "- M{at} goes back to the previous entry: it takes back M{undone}, the change just before it about the same thing, so the value is again the one M{restored} gives."


def subject_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{3,}", text.lower()) if word not in REVERT_STOP}


def revert_lines(groups: list[list[MemoryPair]], token: str) -> list[str]:
    # Copies of an entry differ by slips of spelling: what any copy says plainly, the entry says.
    copies = [[read_form(statement(pair, token)) for pair in group] for group in groups]
    reverts = [any(REVERT_RE.search(text) for text in group) for group in copies]
    words = [set().union(*(subject_words(text) for text in group)) for group in copies]
    lines = []
    for at, group in enumerate(copies):
        declined = any(DECLINED_RE.search(text) for text in group)
        in_error = any(IN_ERROR_RE.search(text) for text in group)
        if not declined and not in_error and not reverts[at]:
            continue
        related = [i for i in range(at) if not any(ASIDE_RE.match(text) for text in copies[i]) and len(words[at] & words[i]) >= 2]
        if len(related) < 2 or any(reverts[i] for i in related[-2:]):
            continue
        lines.append((IN_ERROR_LINE if in_error else DECLINED_LINE if declined else REVERT_LINE).format(at=at + 1, undone=related[-1] + 1, restored=related[-2] + 1))
    return lines


COPY_SIMILARITY = 0.85


def stamp(timestamp: str) -> str:
    # A note's full filing time, to the minute ("2025-06-18 10:12").
    return timestamp[:16].replace("T", " ")


def filed_view(records: list[MemoryPair], token: str = "") -> tuple[list[list[MemoryPair]], str]:
    # The notes in the order they were saved, each with its filing time. Copies of one statement saved at the same time
    # (the same line kept in several places) are one entry, shown once with the number of copies; the same statement
    # saved again later is a separate entry in its own place.
    ordered: list[list[MemoryPair]] = []
    for pair in sorted(records, key=lambda p: (p.timestamp, p.pair_id)):
        text = statement(pair, token).lower()
        # A copy is saved at the same minute and reads the same apart from slips of spelling.
        copy = next((group for group in ordered if stamp(group[0].timestamp) == stamp(pair.timestamp) and difflib.SequenceMatcher(None, statement(group[0], token).lower(), text).ratio() >= COPY_SIMILARITY), None)
        if copy is None:
            ordered.append([pair])
        else:
            copy.append(pair)
    blocks = []
    for mark, group in enumerate(ordered, start=1):
        pair = group[0]
        if not pair.timestamp:
            blocks.append(undated_block(mark, pair))
            continue
        # Every copy's own text stays shown under the entry's one mark (copies differ only by slips of spelling).
        copies = f" (one entry saved {len(group)} times at this time; each copy below)" if len(group) > 1 else ""
        texts = "\n".join(f"User: {copy.prompt}" for copy in group)
        blocks.append(f"[M{mark}] {stamp(pair.timestamp)}{copies}\n{texts}\nAssistant: {pair.response}")
    return ordered, "\n\n".join(blocks)


async def consult(llm: LLM, tally: TokenTally, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, effort: str, deadline: float, outcome: Outcome, what: str) -> str | None:
    for level in (effort, "low"):
        if deadline - time.monotonic() < MIN_SECONDS:
            outcome.events.append(f"{what}: no time left")
            return None
        try:
            result = await llm.chat(messages, None, deadline=deadline, max_tokens=max_tokens, reasoning_effort=level)
        except LLMError as exc:
            tally.add(exc.usage)
            log.error("case=%s %s call failed: %s", req.case_id, what, exc)
            outcome.events.append(f"{what} llm failure: {exc}")
            return None
        tally.add(result)
        outcome.model_calls += 1
        if result.content.strip():
            return result.content
        outcome.events.append(f"{what} empty reply finish={result.finish_reason} effort={level}")
    return None


def short_system(operator: str, own: str) -> str:
    if not operator.strip():
        return own
    return own + "\n\n" + OPERATOR_SEAM + "\n" + operator.strip()


def lead_view(groups: list[list[MemoryPair]], token: str, header: str) -> str:
    statements = [statement(group[0], token) for group in groups]
    if len(statements) < 2 or any(len(text) > LEAD_MAX_STATEMENT_CHARS for text in statements):
        return ""
    return header + "\n" + "\n".join(f"{mark}. {text}" for mark, text in enumerate(statements, start=1))


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome) -> bool:
    if deadline - time.monotonic() < MIN_SECONDS:
        outcome.events.append("deciding call: no time left")
        return False
    start = len(messages)
    await engine.converse(req, messages, None, effort, max_tokens, deadline, outcome)
    if outcome.content.strip():
        return True
    engine.carried.extend(made_calls(messages[start:]))
    return False


def made_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("role") == "tool" or (message.get("role") == "assistant" and message.get("tool_calls"))]


def one_value_step(message: str) -> str:
    return f" {ONE_VALUE_STEP}" if guide_records.asks_one_value(message) else ""


def program_messages(system: str, shown: str, note: str, message: str) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": f"{shown}\n\n{note}{MESSAGE_HEADER}\n{message}"}]


class ShortPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, drafts: dict[str, asyncio.Future[str | None]]) -> None:
        self.engine = engine
        self.llm = engine.llm
        self.tally = engine.tally
        self.drafts = drafts
        self.effort = effort
        self.max_tokens = max_tokens

    async def call(self, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, deadline: float, outcome: Outcome, what: str) -> str | None:
        return await consult(self.llm, self.tally, req, messages, max_tokens, self.effort, deadline, outcome, what)

    async def answer(self, req: RunRequest, records: list[MemoryPair], token: str, deadline: float, outcome: Outcome) -> bool:
        groups, notes = filed_view(records, token)
        lead = lead_view(groups, token, FILED_ORDER_HEADER)
        reverts = revert_lines(groups, token)
        shown = (f"{lead}\n\n" if lead else "") + f"{NOTES_HEADER}\n\n{notes}" + ("\n\n" + REVERT_HEADER + "\n" + "\n".join(reverts) if reverts else "")
        system = short_system(req.system_prompt, " ".join([FILED_PROGRAM_SYSTEM, FILED_ORDER_NOTE, *guide_records.program_notes(req.user_input)]))
        asked = asked_part(req.user_input)
        key = hashlib.sha256(json.dumps([normalize_user_id(req.user_id), system, shown, asked]).encode()).hexdigest()
        same_role = f" {guide_records.SAME_ROLE_NOTE}" if guide_records.WHO_RUNS_RE.search(fold(read_form(req.user_input))) else ""
        draft = await self.shared_draft(req, key, program_messages(system, shown, "", f"{req.user_input}\n\n{DRAFT_STEPS}{one_value_step(req.user_input)}{same_role}"), deadline, outcome)
        note = SHARED_DRAFT_NOTE.format(asked=asked, draft=draft.strip()) + "\n\n" if draft is not None else ""
        outcome.events.append(f"short path (filed order) records={len(records)}{' shared draft' if note else ''}")
        return await decide(self.engine, req, program_messages(system, shown, note, f"{req.user_input}\n\n{DECIDE_STEPS}{one_value_step(req.user_input)}{same_role}"), self.effort, self.max_tokens, deadline, outcome)

    async def shared_draft(self, req: RunRequest, key: str, messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> str | None:
        held = self.drafts.get(key)
        if held is not None:
            return await self.earlier_draft(held, deadline, outcome)
        return await self.first_draft(req, key, messages, deadline, outcome)

    async def earlier_draft(self, held: asyncio.Future[str | None], deadline: float, outcome: Outcome) -> str | None:
        try:
            draft = await asyncio.wait_for(asyncio.shield(held), max(0.01, deadline - time.monotonic() - SHARED_WAIT_RESERVE))
        except TimeoutError:
            outcome.events.append("shared draft: the draft for an earlier rewording over the same notes is not ready in time")
            return None
        outcome.events.append("shared draft: written for an earlier rewording over the same notes" if draft is not None else "shared draft: none")
        return draft

    async def first_draft(self, req: RunRequest, key: str, messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> str | None:
        held: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
        self.drafts[key] = held
        while len(self.drafts) > READINGS_HELD:
            del self.drafts[next(iter(self.drafts))]
        draft: str | None = None
        try:
            reply = await self.call(req, messages, self.max_tokens, deadline, outcome, "shared draft")
            if drafted(reply):
                draft = reply
        finally:
            if draft is None and self.drafts.get(key) is held:
                del self.drafts[key]
            held.set_result(draft)
        outcome.events.append("shared draft: written here" if draft is not None else "shared draft: none written")
        return draft


def first_line(text: str) -> str:
    return text.strip().splitlines()[0][:120] if text.strip() else ""


def record_view(notes: list[MemoryPair]) -> str:
    return "\n\n".join(record_block(mark, pair) for mark, pair in enumerate(notes, start=1))


def passage_head(mark: int, pair: MemoryPair, labels: dict[str, str] | None = None) -> str:
    label = labels[pair.pair_id] if labels is not None else f"M{mark}"
    return f"[{label}] {pair.timestamp[:10]}" if pair.timestamp else f"[{label}]"


def dated_passages(notes: list[MemoryPair], excerpts: dict[str, str], labels: dict[str, str] | None = None) -> list[tuple[str, str]]:
    return [(passage_head(mark, pair, labels), paragraph) for mark, pair in enumerate(notes, start=1) if pair.pair_id in excerpts for paragraph in paragraphs(excerpts[pair.pair_id])]


def passages_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, labels: dict[str, str] | None = None) -> str:
    return PASSAGES_HEADER.format(phrase=phrase) + "\n\n" + "\n\n".join(f"{head} {paragraph}" for head, paragraph in dated_passages(notes, excerpts, labels))


def other_paragraphs(notes: list[MemoryPair], pairs: list[MemoryPair]) -> Counter[frozenset[str]]:
    held = {pair.pair_id for pair in notes}
    out: Counter[frozenset[str]] = Counter()
    for pair in pairs:
        if pair.pair_id in held:
            continue
        for text in paragraphs(pair.prompt):
            words = tokens(text)
            if len(words) <= RECUR_MAX_WORDS:
                out[frozenset(words)] += 1
    return out


def passage_shape(text: str, phrase: str) -> frozenset[str]:
    asked = phrase.split()
    return frozenset(word for word in tokens(text) if not any(typo_of(part, word) for part in asked))


def shared_words(shape: frozenset[str], other: frozenset[str], misspelt: dict[tuple[str, str], bool]) -> int:
    exact = len(shape & other)
    if exact == len(shape):
        return exact
    rest = [word for word in other if word not in shape]
    return exact + sum(1 for word in shape if word not in other and len(word) > RECUR_TYPO_WORD and any(typo_once(word, seen, misspelt) for seen in rest))


def typo_once(word: str, seen: str, misspelt: dict[tuple[str, str], bool]) -> bool:
    key = (word, seen)
    if key not in misspelt:
        misspelt[key] = typo_of(word, seen)
    return misspelt[key]


def recurs(shape: frozenset[str], others: Counter[frozenset[str]], misspelt: dict[tuple[str, str], bool]) -> bool:
    if not shape:
        return True
    need = RECUR_SHARE * len(shape)
    times = 0
    for other, seen in others.items():
        if abs(len(other) - len(shape)) > 2 * RECUR_EXTRA_WORDS:
            continue
        if len(shape & other) + sum(1 for word in shape if word not in other and len(word) > RECUR_TYPO_WORD) < need:
            continue
        shared = shared_words(shape, other, misspelt)
        if shared >= need and len(other) - shared <= RECUR_EXTRA_WORDS:
            times += seen
            if times >= RECUR_TIMES:
                return True
    return False


def dated_sentences(notes: list[MemoryPair], excerpts: dict[str, str], labels: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    # Each sentence of the passages with its note's heading, and the sentence before it in the same passage.
    out: list[tuple[str, str, str]] = []
    for head, passage in dated_passages(notes, excerpts, labels):
        before = ""
        for sentence in SENTENCE_END.split(passage):
            if sentence.strip():
                out.append((head, sentence.strip(), before))
                before = sentence.strip()
    return out


def names_thread(sentence: str, phrase: str) -> bool:
    # As written and as read: reading slips can turn a name into a word ("unisys" into "units"), and a slip can hide a word of the name.
    low = f"{sentence} {read_form(sentence)}".lower()
    words = [word for word in phrase.lower().split() if len(word) > 2]
    return sum(word in low for word in words) >= max(1, len(words) - 1)


def state_sentences(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, labels: dict[str, str] | None = None) -> list[tuple[str, str]]:
    found = []
    for head, sentence, _ in dated_sentences(notes, excerpts, labels):
        read = read_form(sentence)
        # A word of the thread's own name ("moving to garden road") says nothing about its state.
        told = re.sub(re.escape(read_form(phrase)), " ", read_form(read_slips(sentence, STATE_WORDS)), flags=re.IGNORECASE)
        if guide_records.STATE_RE.search(told) and not guide_records.NOT_STATE_RE.search(read) and names_thread(sentence, phrase):
            found.append((head, sentence))
    return found


def action_sentences(notes: list[MemoryPair], excerpts: dict[str, str], labels: dict[str, str] | None = None) -> list[tuple[str, str]]:
    # A next action in a sentence of its own: where it says only "them", the sentence before it names who that is.
    found = []
    for head, sentence, before in dated_sentences(notes, excerpts, labels):
        if not ACTION_CUE_RE.search(fold(sentence, ACTION_CUE_WORDS, ACTION_CUE_LOOKALIKES)):
            continue
        if FULL_NAME_RE.search(sentence):
            found.append((head, sentence))
        elif before and NAMELESS_ACTION_RE.search(sentence) and FULL_NAME_RE.search(before):
            found.append((head, f"{before} {sentence}"))
    return found


def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False) -> list[tuple[str, str]]:
    passages = dated_passages(notes, excerpts, labels)
    if not passages:
        return []
    others = other_paragraphs(notes, pairs)
    misspelt: dict[tuple[str, str], bool] = {}
    kept = [passage for passage in passages if not recurs(passage_shape(passage[1], phrase), others, misspelt)] or passages
    last = kept[-1]
    picks = [(RECENT_LINE, f"{last[0]} {last[1]}")]
    if holder:
        handed = latest_handover(notes, excerpts, labels)
        if handed is not None:
            picks.append((RECENT_HANDOVER_LINE, f"{handed[0]} {handed[1]}"))
        return picks
    if next_step:
        actions = action_sentences(notes, excerpts, labels) or [passage for passage in passages if ACTION_CUE_RE.search(fold(passage[1], ACTION_CUE_WORDS, ACTION_CUE_LOOKALIKES)) and FULL_NAME_RE.search(passage[1])]
        if actions:
            if len(actions) > 1:
                picks.append((RECENT_REPLACED_LINE, f"{actions[-2][0]} {actions[-2][1]}"))
            picks.append((RECENT_ACTION_LINE, f"{actions[-1][0]} {actions[-1][1]}"))
            return picks
    named = next((passage for passage in reversed(kept) if full_names(passage[1], pairs)), None)
    if named is not None and named is not last:
        picks.append((RECENT_PERSON_LINE, f"{named[0]} {named[1]}"))
    return picks


def latest_handover(notes: list[MemoryPair], excerpts: dict[str, str], labels: dict[str, str] | None = None) -> tuple[str, str] | None:
    sentence = next((row for row in reversed(dated_sentences(notes, excerpts, labels)) if HANDOVER_RE.search(fold(read_slips(row[1], HANDOVER_SLIPS), HANDOVER_CUE_WORDS, ACTION_CUE_LOOKALIKES)) and FULL_NAME_RE.search(row[1])), None)
    if sentence is not None:
        return sentence[0], sentence[1]
    return next((passage for passage in reversed(dated_passages(notes, excerpts, labels)) if HANDOVER_RE.search(fold(read_slips(passage[1], HANDOVER_SLIPS), HANDOVER_CUE_WORDS, ACTION_CUE_LOOKALIKES)) and FULL_NAME_RE.search(passage[1])), None)


def handover_names(notes: list[MemoryPair], excerpts: dict[str, str], pairs: list[MemoryPair]) -> list[str]:
    handed = latest_handover(notes, excerpts)
    return full_names(handed[1], pairs) if handed is not None else []


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False) -> str:
    picks = recent_picks(notes, excerpts, phrase, pairs, labels, holder, next_step)
    if not picks:
        return ""
    return RECENT_HEADER + "\n" + "\n".join(line.format(phrase=phrase, passage=passage) for line, passage in picks)


def drafted(reply: str | None) -> bool:
    return bool(parse_slot(reply or "")[1])


class TopicPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, max_chars: int) -> None:
        self.engine = engine
        self.effort = effort
        self.max_tokens = max_tokens
        self.max_chars = max_chars

    def fits(self, notes: list[MemoryPair]) -> bool:
        return sum(record_size(pair) for pair in notes) <= self.max_chars

    def with_cards(self, notes: list[MemoryPair], pairs: list[MemoryPair], named: list[str] | None = None) -> list[MemoryPair]:
        named = named or full_names("\n".join(pair.prompt + "\n" + pair.response for pair in notes), pairs)
        held = {pair.pair_id for pair in notes}
        out = list(notes)
        for pair in cards_for(named, pairs):
            if pair.pair_id not in held and self.fits(out + [pair]):
                out.append(pair)
                held.add(pair.pair_id)
        return by_date(out)

    async def answer(self, req: RunRequest, found: TopicNotes, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> bool:
        notes = found.notes
        if not self.fits(notes):
            outcome.events.append(f"topic path: notes over {self.max_chars} chars; records lane decides")
            return False
        phrase = " ".join(found.topic.phrase)
        guide = guide_records.read(req.user_input)
        # A question on the order of a thread's firms or on a figure's whole chain turns on no one passage.
        whole_chain = bool(guide_records.ORDER_ASK_RE.search(fold(read_form(req.user_input))))
        # Who holds a thread and what comes next each turn on one passage; the rest of a long thread only offers later states and
        # tasks to take for them, so the passage goes to the deciding call.
        from_passage = None if whole_chain else passage_messages(req, notes, found.excerpts, phrase, pairs)
        if from_passage is not None:
            outcome.events.append(f"topic passage phrase={phrase!r} records={len(notes)}")
            if await decide(self.engine, req, from_passage, self.effort, self.max_tokens, deadline, outcome):
                return True
        if CONTACT_RE.search(req.user_input):
            named = await self.named_in_reading(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
            handed = handover_names(notes, found.excerpts, pairs) if guide_records.read(req.user_input).asks_holder else []
            notes = self.with_cards(notes, pairs, list(dict.fromkeys((named or []) + handed)) or None)
        # The latest passages cannot show what each record says, nor a figure's whole chain of changes, so a question about the
        # records disagreeing or a figure gets no draft from them.
        draft = "" if whole_chain or from_passage is not None or guide.asks_figure or (guide.asks_holder and guide.asks_contact) else await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft)
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        # With its own draft in hand the model only has to see whether a note plainly shows it wrong.
        decided = await decide(self.engine, req, messages, "low" if draft else self.effort, self.max_tokens, deadline, outcome)
        # No reply at all from the deciding call: the model's draft from this same request goes out (W7 shape recovery).
        if draft and not decided:
            outcome.content = draft
            outcome.answer = parse_slot(draft)[1]
            outcome.events.append("empty reply: draft sent")
            return True
        return decided

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        guide = guide_records.read(req.user_input)
        # A question on the next step, the state, the lesson or whether records agree is first read from the passages that give it: a
        # later "wrapped up" does not take a next step away, and a latest "the ball is with" holds no state.
        turns_on = ((guide.asks_next_step and step_passages(notes, excerpts, phrase, pairs))
                    or (guide_records.asks_state_only(guide) and state_passages(notes, excerpts, phrase, pairs))
                    or (guide.asks_holder and not guide.asks_contact and owner_passages(notes, excerpts, phrase, pairs))
                    or (guide.asks_lesson and lesson_passages(notes, excerpts, phrase, pairs))
                    or (guide.asks_disagreement and disagree_passages(notes, excerpts, phrase, pairs)))
        if turns_on:
            passages = turns_on.split("\n", 1)[1]
            key = SpellingKey([pair.prompt for pair in pairs]).lines([passages])
            shown = f"{DRAFT_PASSAGES_HEADER}\n{passages}" + (f"\n\n{key}" if key else "")
            asked = f"{req.user_input}\n\n{STATES_DIFFER_LINE}" if guide.asks_disagreement else req.user_input
            messages = [{"role": "system", "content": short_system(req.system_prompt, topic_system(req.user_input))}, {"role": "user", "content": f"{shown}\n\n{MESSAGE_HEADER}\n{asked}"}]
        else:
            picks = recent_picks(notes, excerpts, phrase, pairs)
            if not picks:
                return ""
            key = SpellingKey([pair.prompt for pair in pairs]).lines([passage for _, passage in picks])
            passages = "\n".join(passage for _, passage in picks) + (f"\n\n{key}" if key else "")
            messages = [{"role": "system", "content": short_system(req.system_prompt, " ".join([LATEST_SYSTEM, *guide_records.notes(req.user_input)]))}, {"role": "user", "content": LATEST_BRIEF.format(passages=passages, message=req.user_input)}]
        reply = await consult(self.engine.llm, self.engine.tally, req, messages, self.max_tokens, self.effort, deadline, outcome, "latest passages reading")
        written = drafted(reply)
        outcome.events.append(f"latest passages reading: {'draft' if written else 'no draft'}")
        return (reply or "").strip() if written else ""

    async def named_in_reading(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> list[str] | None:
        reply = await consult(self.engine.llm, self.engine.tally, req, topic_messages(req, notes, excerpts, phrase, pairs) + [{"role": "user", "content": PERSON_BRIEF}], self.max_tokens, self.effort, deadline, outcome, "thread reading")
        named = full_names(SPACE.sub(" ", reply or ""), pairs)
        outcome.events.append(f"thread reading named {len(named)}")
        return named or None


def passage_messages(req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> list[dict[str, Any]] | None:
    guide = guide_records.read(req.user_input)
    found = (guide.asks_next_step and step_passages(notes, excerpts, phrase, pairs)) or (guide.asks_holder and owner_passages(notes, excerpts, phrase, pairs)) or (guide.asks_figure and figure_passages(notes, excerpts, phrase, pairs)) or (guide.asks_lesson and lesson_passages(notes, excerpts, phrase, pairs))
    if not found:
        return None
    passages = found.split("\n", 1)[1]
    cards = []
    if guide.asks_holder and guide.asks_contact:
        # The holder's address is in the short notes on that person, which the thread does not hold.
        cards = cards_for(full_names(passages, pairs), pairs)
        if not cards:
            return None
    # Spelling help is for a task or a lesson in the note's words; names and figures are copied as written.
    key = SpellingKey([pair.prompt for pair in pairs]).lines([passages]) if guide.asks_next_step or guide.asks_lesson else ""
    shown = f"{DRAFT_PASSAGES_HEADER}\n{passages}" + (f"\n\n{key}" if key else "")
    if cards:
        shown += f"\n\n{PASSAGE_CARDS_HEADER}\n" + "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt.strip()}" for pair in by_date(cards))
    return [{"role": "system", "content": short_system(req.system_prompt, f"{topic_system(req.user_input).replace(' ' + NOT_STATED_LINE, '')} {PASSAGE_ONE_ASK}")}, {"role": "user", "content": f"{shown}\n\n{MESSAGE_HEADER}\n{req.user_input}" + (f"\n\n{NEXT_TASK_LINE}" if guide.asks_next_step else f"\n\n{OPEN_AMOUNT_LINE}" if guide.asks_figure and COMMITTED_RE.search(read_form(passages)) else "")}]


def step_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # The passage that gives a thread's next step.
    picks = [pick for pick in recent_picks(notes, excerpts, phrase, pairs, next_step=True) if pick[0] == RECENT_ACTION_LINE]
    if not any(line == RECENT_ACTION_LINE for line, _ in picks):
        return ""
    view = "\n".join(line.format(phrase=phrase, passage=passage) for line, passage in picks)
    return f"{STEP_PASSAGES_HEADER}\n{view}"


def state_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # The sentence that gives a thread's latest state.
    found = state_sentences(notes, excerpts, phrase)
    if not found:
        return ""
    line = RECENT_STATE_LINE.format(phrase=phrase, passage=f"{found[-1][0]} {found[-1][1]}")
    return f"{STEP_PASSAGES_HEADER}\n{line}"


def lesson_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # The sentence that gives what the user took from a thread.
    found = [(head, sentence) for head, sentence, _ in dated_sentences(notes, excerpts) if LESSON_SENTENCE_RE.search(read_form(sentence)) and not LESSON_NOT_RE.search(sentence)]
    if not found:
        return ""
    line = RECENT_LESSON_LINE.format(phrase=phrase, passage=f"{found[-1][0]} {found[-1][1]}")
    return f"{STEP_PASSAGES_HEADER}\n{line}"


def owner_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # The sentence that puts a person in charge of a thread.
    handed = latest_handover(notes, excerpts)
    if handed is None:
        return ""
    line = RECENT_HANDOVER_LINE.format(phrase=phrase, passage=f"{handed[0]} {handed[1]}")
    return f"{STEP_PASSAGES_HEADER}\n{line}"


def same_question(asked: str, seen: str) -> bool:
    # The same asking sentence over the same notes, a few slips of the keyboard apart.
    return difflib.SequenceMatcher(None, asked, seen).ratio() >= SAME_QUESTION_RATIO


def record_rows(record: str) -> list[str]:
    # A record's lines as written; each entry of a listed JSON array stands on one line so that it can be kept whole.
    listed = record.find("[\n")
    if listed >= 0:
        try:
            rows = json.loads(record[listed:record.rindex("]") + 1])
        except ValueError:
            rows = None
        if isinstance(rows, list):
            return record[:listed].split("\n") + [json.dumps(row, ensure_ascii=False) for row in rows]
    return record.split("\n")


def row_values(row: str) -> frozenset[str]:
    # The values one line of a case file names, however the file lays that line out. Only for telling whether two files say the
    # same thing: nothing read here reaches the model.
    row = ROW_PREFIX_RE.sub("", CODE_TAG_RE.sub("", row)).strip().lower()
    if row.startswith("{"):
        try:
            return frozenset(str(value) for value in json.loads(row).values()) - ROW_NOT_VALUES
        except (ValueError, AttributeError):
            pass
    quoted = QUOTED_VALUE_RE.findall(row)
    if quoted:
        rest = QUOTED_VALUE_RE.sub(" ", row)
        return frozenset([*quoted, *ROW_FIGURE_RE.findall(rest), *ROW_CHANGE_RE.findall(rest)])
    cells = row.strip("|").split("|") if row.startswith("|") else row.split(",")
    return frozenset(cell.strip() for cell in cells) - ROW_NOT_VALUES


def same_file(message: str, pairs: list[MemoryPair]) -> tuple[str, str]:
    # Whether two case files say the same thing about what the message asks, under another code and in another layout, unrelated
    # lines aside: a hash of the values on the lines joined to the ids it names, and those lines as written, for the same-question
    # call to look over. The hash only says when an earlier reply may be put to the model again.
    asked = EVENT_ID_RE.findall(message)
    file = next((token for token in identifier_tokens(message) if not any(name.startswith(token) or token.startswith(name[:6]) for name in asked)), "") if asked else ""
    held = sorted((pair for pair in pairs if file and file in pair.prompt.lower()), key=lambda p: (p.timestamp, p.pair_id))
    if not held:
        return "", ""
    rows = [(at, row) for at, pair in enumerate(held) for row in record_rows(pair.prompt)]
    seen = set(asked)
    while True:
        reached = {name for _, row in rows for name in EVENT_ID_RE.findall(row) if seen & set(EVENT_ID_RE.findall(row))} - seen
        if not reached:
            break
        seen |= reached
    lines: list[str] = []
    before: list[str] = []
    heading = ""
    place = -1
    for at, row in rows:
        if at != place:
            place, heading = at, ""
        named = set(EVENT_ID_RE.findall(row))
        if seen & named:
            lines.append(f"{heading} => {row}" if heading and CELLS_RE.search(row) else row)
            if heading and not CELLS_RE.search(row) and heading not in before:
                before.append(heading)
        elif not named and ("," in row or "|" in row) and not set(row) <= TABLE_RULE and file not in row.lower():
            heading = row
    if not lines:
        return "", ""
    head = "\n".join([held[0].prompt.split("\n")[0], *before])
    values = {row_values(line.split(" => ")[-1]) for line in lines}
    key = hashlib.sha256(repr((held[0].prompt.split("\n")[0].lower().replace(file, ""), sorted(sorted(value) for value in values))).encode()).hexdigest()
    return key, EVENT_SHOWN.format(start=asked[0]) + "\n" + head + "\n" + "\n".join(lines)


def note_words(records: list[MemoryPair], token: str) -> frozenset[str]:
    # The words and figures of the notes, without the code they are filed under: the same notes laid out another way share them.
    return frozenset(re.findall(r"[a-z0-9][a-z0-9.@-]*", " ".join(pair.prompt for pair in records).lower())) - {token}


def named_in(asked: str, token: str) -> frozenset[str]:
    # The codes and figures a question names, other than the file's own: two questions naming different ones are different questions.
    return frozenset(found for found in re.findall(r"[a-z0-9-]*\d[a-z0-9-]*", asked.lower()) if found != token)


def same_notes(words: frozenset[str], seen: frozenset[str]) -> bool:
    return len(words & seen) >= SAME_FILE_SHARE * len(words | seen)


async def repeat_reply(engine: RecordsEngine, req: RunRequest, question: str, earlier: str, max_tokens: int, deadline: float, outcome: Outcome, by_values: bool = False) -> bool:
    # A question asked again in other words over the same notes: the model sees its earlier reply and sends it again, or says
    # the message asks something else, in which case the request is decided as usual.
    messages = [{"role": "system", "content": short_system(req.system_prompt, SAME_QUESTION_SYSTEM)}, {"role": "user", "content": (SAME_FACTS_LINE if by_values else SAME_WORDS_LINE) + "\n\n" + SAME_QUESTION_BRIEF.format(question=question, reply=earlier, message=req.user_input)}]
    # A long reasoning here is the model working the answer out again, which the call is there to avoid; such a call stops short and is tried once more.
    reply = ""
    for _ in range(SAME_QUESTION_TRIES):
        try:
            result = await engine.llm.chat(messages, None, deadline=deadline, max_tokens=min(max_tokens, SAME_QUESTION_MAX_TOKENS), reasoning_effort="low")
        except LLMError as exc:
            engine.tally.add(exc.usage)
            outcome.events.append(f"same question: llm failure: {exc}")
            return False
        engine.tally.add(result)
        outcome.model_calls += 1
        reply = result.content.strip()
        if reply and result.finish_reason != "length":
            break
        reply = ""
    # Only a reply that is that one word says so; a reply that merely contains it ships.
    if not reply or reply.rstrip(".").strip() == SAME_QUESTION_NO:
        outcome.events.append("same question: decided anew")
        return False
    outcome.content = reply
    outcome.answer = parse_slot(reply)[1]
    outcome.events.append("same question: earlier reply sent again")
    return True


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


def disagree_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # Every sentence giving a state: which of them are the versions that differ is the model's to read.
    found = state_sentences(notes, excerpts, phrase)
    if len(found) < 2:
        return ""
    lines = "\n".join(RECENT_STATES_LINE.format(phrase=phrase, passage=f"{head} {sentence}") for head, sentence in found)
    return f"{STEP_PASSAGES_HEADER}\n{lines}"


def figure_sentences(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str) -> list[tuple[str, str]]:
    # Sentences of a thread that give it a figure, oldest first; a clause after a semicolon goes with the figure before it.
    found: list[tuple[str, str]] = []
    joined = False
    for head, sentence, before in dated_sentences(notes, excerpts):
        plain = REFERENCE_RE.sub(" ", sentence)
        figure = bool(THREAD_FIGURE_RE.search(plain))
        follows = joined and bool(before) and before.endswith(";")
        if figure and not REFERENCE_WORDS_RE.search(sentence) and not SCHEDULE_SLIP_RE.search(read_form(sentence)) and (follows or names_thread(sentence, phrase) or FIGURE_WORDS_RE.search(sentence)):
            found.append((head, sentence))
            joined = True
        else:
            joined = False
    return found


def figure_passages(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair]) -> str:
    # The sentences that give a thread's figure.
    found = figure_sentences(notes, excerpts, phrase)
    if not found:
        return ""
    lines = "\n".join(RECENT_FIGURE_LINE.format(passage=f"{head} {sentence}") for head, sentence in found)
    return f"{STEP_PASSAGES_HEADER}\n{lines}"


def topic_messages(req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], draft: str = "") -> list[dict[str, Any]]:
    guide = guide_records.read(req.user_input)
    # The whole thread always goes to the model. Beside it, as an unchecked place to start, the passage this kind of question turns
    # on: the rest of a long thread offers other tasks, states and figures to confuse it with.
    recent = ((guide.asks_next_step and step_passages(notes, excerpts, phrase, pairs))
              or (guide_records.asks_state_only(guide) and state_passages(notes, excerpts, phrase, pairs))
              or (guide.asks_holder and not guide.asks_contact and not guide.asks_next_step and owner_passages(notes, excerpts, phrase, pairs))
              or (guide.asks_lesson and lesson_passages(notes, excerpts, phrase, pairs))
              or (guide.asks_figure and not guide.asks_next_step and figure_passages(notes, excerpts, phrase, pairs))
              or (guide.asks_disagreement and disagree_passages(notes, excerpts, phrase, pairs))
              or recent_view(notes, excerpts, phrase, pairs, holder=guide.asks_holder, next_step=guide.asks_next_step))
    beside = f"\n\n{recent}" if recent else ""
    key = SpellingKey([pair.prompt for pair in pairs]).lines([paragraph for _, paragraph in dated_passages(notes, excerpts)])
    beside += f"\n\n{key}" if key else ""
    if draft:
        # The rules for this kind of question went into the draft; here the model only judges it against the whole thread.
        about = DRAFT_STATES_DIFFER if guide.asks_disagreement else DRAFT_NOT_THE_OWNER if guide.asks_holder else DRAFT_NEXT_STANDS if guide.asks_next_step else ""
        return [{"role": "system", "content": short_system(req.system_prompt, f"{DRAFT_CHECK_SYSTEM} {about}".strip())}, {"role": "user", "content": DRAFT_CHECK_BRIEF.format(notes=f"{NOTES_HEADER}\n\n{record_view(notes)}{beside}", message=req.user_input, draft=draft)}]
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{beside}\n\n{MESSAGE_HEADER}\n{req.user_input}"
    return [{"role": "system", "content": short_system(req.system_prompt, topic_system(req.user_input))}, {"role": "user", "content": user}]


def topic_system(message: str) -> str:
    return " ".join([TOPIC_SYSTEM, *guide_records.notes(message)])


@dataclass(frozen=True)
class TopicNotes:
    topic: Topic
    notes: list[MemoryPair]
    excerpts: dict[str, str]


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


def names_someone_else(question: str, chosen: list[MemoryPair], pairs: list[MemoryPair]) -> bool:
    # A name inside the question that the thread never uses but another short note does: the question is about that note, whatever
    # words it shares with the thread.
    text = "\n".join(pair.prompt + "\n" + pair.response for pair in chosen)
    others = [pair.prompt for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS]
    for found in INNER_NAME_RE.finditer(question):
        word = found.group(1)
        if word.lower() not in WORDS and not re.search(r"\b" + word + r"\b", text) and any(re.search(r"\b" + word + r"\b", prompt) for prompt in others):
            return True
    return False


def find_topic(question: str, pairs: list[MemoryPair], min_density: int, max_chars: int) -> TopicNotes | None:
    # A contact question naming a person in full asks about that person, whatever event it mentions on the way.
    if not pairs or QUOTE_RE.search(question) or full_names(question, pairs) or (CONTACT_RE.search(read_form(question)) and names_a_person(question)):
        return None
    index = TopicIndex(pairs)
    topic = index.topic(question)
    if topic is None or topic.densest < min_density:
        return None
    excerpts = index.excerpt(topic)
    dense = [pair for pair in excerpts if PARAGRAPH_BREAK in pair.prompt]
    if len(dense) < MIN_DENSE_NOTES:
        return None
    whole = {pair.pair_id: pair for pair in pairs}
    chosen = [whole[pair.pair_id] for pair in dense]
    room = max_chars - sum(record_size(pair) for pair in chosen)
    for pair in excerpts:
        if PARAGRAPH_BREAK in pair.prompt:
            continue
        size = record_size(whole[pair.pair_id])
        if size <= room:
            chosen.append(whole[pair.pair_id])
            room -= size
    chosen = thread_of(question, chosen, pairs)
    if names_someone_else(question, chosen, pairs):
        return None
    kept = {pair.pair_id for pair in chosen}
    return TopicNotes(topic, by_date(chosen), {pair.pair_id: pair.prompt for pair in excerpts if pair.pair_id in kept})


def topic_lead(question: str, packet: Packet, pairs: list[MemoryPair], min_density: int, max_chars: int) -> tuple[Packet, str]:
    found = find_topic(question, pairs, min_density, max_chars)
    if found is None:
        return packet, ""
    held = {cand.pair.pair_id for cand in packet.records}
    whole = Packet(records=packet.records + [Candidate(pair=pair) for pair in found.notes if pair.pair_id not in held], focused=packet.focused)
    labels = whole.labels()
    phrase = " ".join(found.topic.phrase)
    recent = recent_view(found.notes, found.excerpts, phrase, pairs, labels)
    return whole, passages_view(found.notes, found.excerpts, phrase, labels) + (f"\n\n{recent}" if recent else "")


# A request to drop one note about a person: that person's short notes (with the name each nickname stands for) go
# beside the records, all alike and unranked, so the note to drop and the records that stay are both in view.
PEOPLE_HEADER = "Who the names in this message are, and the user's short notes about them:"


def scratchpad_lead(question: str, packet: Packet, pairs: list[MemoryPair]) -> tuple[Packet, str]:
    # The short note that calls itself the scratchpad of the project a correction names, with the id a call needs.
    names = [name.lower() for found in QUOTE_RE.findall(question) for name in found if name]
    notes = [pair for pair in by_date(pairs) if len(pair.prompt) < SHORT_RECORD_CHARS and "scratchpad" in pair.prompt.lower() and any(name in pair.prompt.lower() for name in names)]
    if not notes:
        return packet, ""
    held = {cand.pair.pair_id for cand in packet.records}
    whole = Packet(records=packet.records + [Candidate(pair=pair) for pair in notes if pair.pair_id not in held], focused=packet.focused)
    return whole, SCRATCHPAD_HEADER + "\n" + "\n".join(f"- pair_id {pair.pair_id}: {pair.prompt}" for pair in notes)


def receipt_lead(question: str, packet: Packet, pairs: list[MemoryPair]) -> tuple[Packet, str]:
    # The short note that calls itself a receipt or scratch note about the person a delete request names, with the id the call needs.
    known = known_aliases(pairs)
    names = [alias for alias in known if re.search(r"\b" + re.escape(alias) + r"\b", question)] + FULL_NAME_RE.findall(question)
    notes = [pair for pair in by_date(pairs) if len(pair.prompt) < SHORT_RECORD_CHARS and RECEIPT_NOTE_RE.search(read_form(pair.prompt)) and any(re.search(r"\b" + re.escape(name) + r"\b", pair.prompt) for name in names)]
    if not notes:
        return packet, ""
    held = {cand.pair.pair_id for cand in packet.records}
    whole = Packet(records=packet.records + [Candidate(pair=pair) for pair in notes if pair.pair_id not in held], focused=packet.focused)
    return whole, RECEIPT_HEADER + "\n" + "\n".join(f"- pair_id {pair.pair_id}: {pair.prompt}" for pair in notes)


def recipient_lead(question: str, packet: Packet, pairs: list[MemoryPair]) -> tuple[Packet, str]:
    # The short note on who a project's numbers or update go to, for a request to send them.
    names = [name.lower() for found in QUOTE_RE.findall(question) for name in found if name]
    notes = [pair for pair in by_date(pairs) if len(pair.prompt + pair.response) < RECIPIENT_NOTE_CHARS and any(name in pair.prompt.lower() for name in names) and RECIPIENT_NOTE_RE.search(f"{pair.prompt} {pair.response}")]
    if not notes:
        return packet, ""
    held = {cand.pair.pair_id for cand in packet.records}
    whole = Packet(records=packet.records + [Candidate(pair=pair) for pair in notes if pair.pair_id not in held], focused=packet.focused)
    return whole, RECIPIENT_HEADER + "\n" + "\n".join(f"- {pair.prompt} {pair.response}".strip() for pair in notes)


def people_lead(question: str, packet: Packet, pairs: list[MemoryPair]) -> tuple[Packet, str]:
    lines = alias_lines(question, pairs)
    named = [name for line in lines if line.startswith("- \u201c") for name in line.split(": ", 1)[1].split(" or ")] + full_names(question, pairs)
    cards = cards_for(list(dict.fromkeys(named)), pairs)
    if not cards:
        return packet, ""
    held = {cand.pair.pair_id for cand in packet.records}
    whole = Packet(records=packet.records + [Candidate(pair=pair) for pair in cards if pair.pair_id not in held], focused=packet.focused)
    return whole, PEOPLE_HEADER + ("\n" + "\n".join(lines) if lines else "") + "\n" + "\n".join(f"- {pair.prompt}" for pair in cards)


def nicknames(pairs: list[MemoryPair]) -> set[str]:
    return {alias for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS for alias in ALIAS_RE.findall(pair.prompt)}


SETTING_READING_SYSTEM = "You read a user's own notes about one of their Ditto settings and one message. Do not answer anything else. A client's or a brand's value is not theirs, and a note may call the setting something else."
SETTING_READING_BRIEF = "{notes}\n\nMessage:\n{message}\n\nWhat value does the user's latest own note keep for the setting this message names, and is it the value the message names? The setting's own word does not count (dark mode is dark, a steel grey accent is steel grey); any other word does (navy is not dark navy). Reply with one line: 'SAME: <the value>', 'DIFFERENT: <what the note keeps>', or 'NOT KEPT' if no note of theirs keeps a value for it."
SETTING_READING_LINE = "Your own earlier reading of these notes, not checked; the notes decide wherever they differ: {reading}\nIf you read them the same way: SAME means nothing needs changing, so no call of any kind, not discover_capabilities or any other look-up, and a reply that it is already set; DIFFERENT or NOT KEPT means the message asks for a change, so call the setter with the value the message names."


async def setting_reading(engine: RecordsEngine, req: RunRequest, notes: str, deadline: float, outcome: Outcome) -> str:
    # An advisory model call, no tools: its reading goes into the deciding prompt as text, and the host reads nothing from it.
    messages = [{"role": "system", "content": short_system(req.system_prompt, SETTING_READING_SYSTEM)}, {"role": "user", "content": SETTING_READING_BRIEF.format(notes=notes, message=req.user_input)}]
    reply = await consult(engine.llm, engine.tally, req, messages, engine.max_tokens, "low", deadline, outcome, "setting reading")
    return SETTING_READING_LINE.format(reading=reply.strip()) if reply and reply.strip() else ""


def thread_of(question: str, notes: list[MemoryPair], pairs: list[MemoryPair]) -> list[MemoryPair]:
    patterns = [re.compile(r"\b" + re.escape(nick) + r"\b") for nick in sorted(nicknames(pairs)) if re.search(r"\b" + re.escape(nick) + r"\b", question)]
    if not patterns:
        return notes
    thread = [pair for pair in notes if any(pattern.search(pair.prompt) for pattern in patterns)]
    if sum(1 for pair in thread if PARAGRAPH_BREAK in pair.prompt) < MIN_THREAD_NOTES:
        return notes
    return thread
