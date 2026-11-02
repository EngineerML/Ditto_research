from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .action import OPERATOR_SEAM, Outcome, TokenTally
from .answer import parse_slot
from .qtype import HOST_NOTE, answer_hint, asked_part, question_kind
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, identifier_tokens, tokens
from .lane import within_one_edit
from .memory.people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS, by_date, cards_for, full_names, person_card
from .memory.topic import Topic, TopicIndex, edits, paragraphs, typo_budget, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_SYSTEM_FORM = SHORT_OPENING + " Reply briefly, then end with one final line 'ANSWER: {answer}'; when several things are asked, give them on that line in the order asked, separated by ' ; '. Write any date in full, with day, month and year, and write a percentage as its figure followed by the word percent (percentage points for a change in one), not with the % sign. When the message asks how to reach or write to someone, or for their current work address, give the contact detail the notes hold for writing to them now, such as their current email address. Give only an address a note states, never one built from their name and workplace; when no note states one, say so and name what the notes do hold about them. When the message takes for granted something that no record shows (a place, stop, person or event the notes never mention), say that no record shows it and what the notes do show, instead of answering zero or none. The notes answer questions about the people, threads, plans and trips they tell, however the message says current, latest, live or now; no web search, address book or directory holds the user's own history, so call none of them for such a question."
PROGRAM_SYSTEM = SHORT_SYSTEM_FORM.format(answer="<only the value asked for, as short as the notes put it, in their words>")
TOPIC_SYSTEM = PROGRAM_SYSTEM.replace(SHORT_OPENING, SHORT_OPENING + " " + NOTES_TOGETHER, 1)
DATED_PROGRAM_SYSTEM = PROGRAM_SYSTEM.replace("with day, month and year.", "with day, month and year, even when the message asks for less.", 1)
SYNONYM_RULE = ("The message may name a thing with other words than the notes do: a synonym, a misspelling, or a description of the role a label the notes define stands for. A note that states it under another name or label still answers it; only a thing no note states under any name is one no record shows.")
CORRECTION_RULE = ("Later notes revise earlier ones in the order they were filed. A note that says an earlier entry was a "
                   "mistake or was logged in error, or that a proposed change was declined or did not go ahead, leaves the value "
                   "that held before that entry or proposal. A note that goes back to an earlier arrangement restores the one it "
                   "names: the previous one is the one that held just before the latest change, the original one the first, "
                   "unless the note states another.")
ONE_VALUE_RULE = ("A question about one thing's status, holder or other value gets the one value that holds for it, never "
                  "the list of values that field can take or what each code means, and the ANSWER line holds that value alone, "
                  "not a sentence about it: the value the field holds, not the field's label. The commissioning party, client or "
                  "paying customer is the organisation that pays for the work; the supplier or vendor is the one paid. A question about "
                  "who holds something now, after every handover, gets the final holder alone, not those who held it before.")
EVENT_DATE_RULE = ("A date or time a note gives for an event tells when that event takes place, not when the note was filed: when "
                   "the question asks which event came first, next or in some place in the sequence, order the events by those "
                   "dates.")
LIST_RULE = ("A question asking for a whole current list (every item, the full list, what someone needs or has now) gets every "
             "item the notes put on it that no later note took off, together with any item a later note added, each as the notes "
             "name it. An address, id or code is copied whole, exactly as the notes give it.")
AFTER_RULE = ("A question that starts from a change as already made (after the change, after the swap, after every recorded "
              "handover or reassignment) asks what holds now: apply that change and every note filed after it, and give the one "
              "value that holds at the latest note, or the whole list as it stands then; never the value right after that "
              "change and never one value per change.")
FORM_RULE = ("A closing line on how to answer (just the name, the status term, both parts, any format) only shapes the answer "
             "to the question before it; it is not another question, even when misspelt. The ANSWER line gives the value in "
             "the notes' own words: an action as the notes word it, without words taken over from the question.")
STEP_RULE = ("In a plan of ordered steps, a step a note marks done, complete or dropped stays closed when a later note only "
             "names a new owner for it, and a step a later note says is open again is open; the first open step is the "
             "earliest step in the plan's order that is not closed, with the owner the latest note gives it.")
DATED_PROGRAM_SYSTEM = DATED_PROGRAM_SYSTEM + " " + SYNONYM_RULE + " " + CORRECTION_RULE + " " + EVENT_DATE_RULE + " " + ONE_VALUE_RULE + " " + LIST_RULE + " " + AFTER_RULE + " " + FORM_RULE + " " + STEP_RULE
# A case file is read as a ledger of values that later entries revise: its system text keeps the shared short-path
# sentences on contact details but not the ones that ask for a "no record" reply, which were written for thread and
# trip questions about things the notes may never mention; the topic path keeps them.
DECLINE_PARTS = (
    "; when no note states one, say so and name what the notes do hold about them.",
    " When the message takes for granted something that no record shows (a place, stop, person or event the notes never mention), say that no record shows it and what the notes do show, instead of answering zero or none.",
    "; only a thing no note states under any name is one no record shows",
)
for _part, _left in zip(DECLINE_PARTS, (".", "", "")):
    assert DATED_PROGRAM_SYSTEM.count(_part) == 1, _part[:60]
    DATED_PROGRAM_SYSTEM = DATED_PROGRAM_SYSTEM.replace(_part, _left, 1)
PROGRAM_NOTE = ("When the message asks who or what holds something after every change the notes record (every handover, "
                "reassignment, swap or revision), it asks for the one value that holds after the last of those changes: the "
                "ANSWER line gives that value alone, never one value per change, and ' ; ' on it separates only different "
                "things the message asks for. A note that goes back to the previous entry or arrangement undoes the last "
                "change before it (after A, then B, then C, going back to the previous one leaves B, not C), and a note that "
                "says an entry was wrong or struck out leaves the value that held before that entry.")
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MARK_RE = re.compile(r"\bM(\d+)\b")
ORDER_SYSTEM = "You read a user's saved notes and put them in the order the user must have written them. Do not answer anything else."
ORDER_BRIEF = "{notes}\n\nThe notes above are listed in no particular order. Judging from their words, work out the order the user must have written them in: a note that refers back to, scraps, replaces or changes an earlier plan, decision or state of the same thing was written after the note that set it. A date mentioned inside a note tells when the thing it describes takes place, not when the note was written. Reply with one line: the marks from the last written to the first written, separated by commas."
MIN_SECONDS = 8.0
ORDER_MAX_TOKENS = 4000
READINGS_HELD = 512
STATE_WAIT_RESERVE = 20.0
EARLIER_REPLY_NOTE = ("An earlier reply to the question \u201c{asked}\u201d, written over these same notes:\n{reply}\n\n"
                      "When the message below asks the same thing in other words, give the same value as that earlier reply.")
EARLIER_REPLY_CHARS = 1500
EARLIER_REPLY_WAIT = 30.0
EARLIER_REPLY_RESERVE = 90.0
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
LEAD_HEADER = "The statements of the notes below, in the order an earlier reading of their words put them:"
FILED_HEADER = "The statements of the notes below, in the order they were filed, earliest first:"
STATE_SYSTEM = "You are Ditto, the user's assistant with long-term memory. You read the user's saved notes about one case file and write down where things stand now. Do not answer anything else."
STATE_BRIEF = ("{notes}\n\nThe notes above are listed in the order they were filed, earliest first. Without being asked anything, write "
               "down where things stand after the last of them: for each thing they keep track of (a value, status, holder, date or "
               "time, plan, list or plan of steps of a named item), one line with the item, what is tracked, the value that holds "
               "now and the marks of the notes it rests on. Apply every note in filing order: a later note replaces an earlier "
               "value; a note that says an entry was a mistake or was struck, or that a proposal or draft did not go ahead, leaves "
               "the value that held before it; a note that goes back to an earlier arrangement restores the value that held just "
               "before the change it undoes; a list holds every item on it now; a plan gives each step as open or closed, with "
               "its owner now. Use the notes' own words and labels.")
STATE_HEADER = "Where things stand after every note, as a separate reading of the notes alone wrote it before the message was read (not checked; the notes decide wherever they differ):"
LEAD_MAX_STATEMENT_CHARS = 1000
PROGRAM_MAX_RECORD_CHARS = 2000
PERSON_BRIEF = "Before the message is answered: which person is it asking about? When it asks about whoever holds, owns or is accountable for something now, that is the person the latest note puts in charge, after every handover the notes record. Only a handover moves it: a note that hands or passes the thing itself to someone, says it is theirs now, or says the previous holder is off it or stepped back. A person who agreed to do a task on it, holds an open action, the next step or the ball, or is being waited on does not become its holder for that. Reply with that person's full name as the notes give it, and nothing else."
RECENT_HEADER = "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:"
RECENT_LINE = "- The most recent passage about “{phrase}”: {passage}"
RECENT_PERSON_LINE = "- The most recent passage about “{phrase}” that names a person: {passage}"
RECENT_ACTION_LINE = "- The most recent passage about “{phrase}” that gives a person a next action: {passage}"
RECENT_HOLDER_LINE = "- The most recent passage about “{phrase}” that hands it to a person or puts a person in charge of it: {passage}"
HANDOVER_CUE_RE = re.compile(
    r"(?:\bhand\w*\b(?: \w+){0,3} (?:to|over)\b|\bhand-?off\b|\bpass(?:ed|es|ing)\b[^.;]{0,40}\bto\b"
    r"|\bpick(?:ed|s)? up\b[^.;]{0,40}\bfrom\b|\bt(?:ook|aken|akes) (?:over|charge|it on)\b|\bnow owns\b|\bowns (?:it|the)\b"
    r"|\bowner|\bownership\b|\bin charge\b|\bstepped (?:back|down|aside)\b|\b(?:is|are) off it\b|'s now\b|\breassign\w*)", re.IGNORECASE)
HOLDER_KINDS = ("owner", "owner-email")
# Kinds that ask where a thread stands: the passage naming a person gives someone a task or the thread, not a state.
STATE_KINDS = ("status", "disagree")
ACTION_CUE_RE = re.compile(r"\b(?:next step|next move|next from them|first action from|follow-up for|open action|is waiting on|the ball is with|agreed to|is going to|will \w+|would \w+|next on)\b", re.IGNORECASE)
RECUR_SHARE = 0.8
RECUR_EXTRA_WORDS = 6
RECUR_TIMES = 2
RECUR_MAX_WORDS = 40
RECUR_TYPO_WORD = 4
LATEST_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
LATEST_BRIEF = "Passages:\n{passages}\n\nMessage:\n{message}"
DRAFT_NOTE = "A draft reply, written from a reading of only the passages picked out above:\n\n{draft}\n\nCheck the draft against every note above, then reply to the message as asked at the start: briefly, ending with the line 'ANSWER: …', without mentioning the draft."


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


STATEMENT_WORD = re.compile(r"[a-z0-9']+")


def same_statement(words: list[str], seen: list[str]) -> bool:
    """Two statements whose words differ only by misspellings within the typo budget, word for word."""
    return len(words) == len(seen) and all(typo_of(word, other) or typo_of(other, word) for word, other in zip(words, seen))


def by_statement(records: list[MemoryPair], token: str) -> list[list[MemoryPair]]:
    """The records grouped by what they state after the token; copies that differ only by misspelt words are one group."""
    groups: list[tuple[list[str], list[MemoryPair]]] = []
    for pair in sorted(records, key=lambda p: (p.timestamp, p.pair_id)):
        words = STATEMENT_WORD.findall(statement(pair, token).lower())
        for seen, members in groups:
            if same_statement(words, seen):
                members.append(pair)
                break
        else:
            groups.append((words, [pair]))
    return [members for _, members in groups]


def copy_words(pair: MemoryPair, token: str) -> list[str]:
    return STATEMENT_WORD.findall(statement(pair, token).lower())


def copy_of(words: list[str], seen: list[str]) -> bool:
    """The same statement saved again: as many words, numbers equal, every other word equal within the typo budget
    (typo_of), or for words of six letters or more within a third of the shorter word's letters."""
    if len(words) != len(seen):
        return False
    for word, other in zip(words, seen):
        if word == other:
            continue
        if any(ch.isdigit() for ch in word + other):
            return False
        if typo_of(word, other) or typo_of(other, word):
            continue
        short = min(word, other, key=len)
        if len(short) < 6 or edits(word, other) > len(short) // 3:
            return False
    return True


def one_copy(notes: list[MemoryPair], token: str) -> list[MemoryPair]:
    """The notes in the order given, with copies of one statement filed at the same minute shown once: the copy whose
    words the other copies share most, then the earliest id. A note without a filing time is never a copy."""
    sets: list[tuple[str, list[list[str]], list[MemoryPair]]] = []
    for pair in notes:
        words = copy_words(pair, token)
        minute = pair.timestamp[:16]
        for held_minute, said, members in sets:
            if minute and held_minute == minute and any(copy_of(words, seen) for seen in said):
                said.append(words)
                members.append(pair)
                break
        else:
            sets.append((minute, [words], [pair]))
    shown: list[MemoryPair] = []
    for _, _, members in sets:
        if len(members) == 1:
            shown.append(members[0])
            continue
        spoken = [set(copy_words(pair, token)) for pair in members]
        shared = [sum(len(words & other) for other in spoken if other is not words) for words in spoken]
        best = min(range(len(members)), key=lambda index: (-shared[index], members[index].pair_id))
        shown.append(members[best])
    return shown


def by_text(groups: list[list[MemoryPair]], token: str) -> list[list[MemoryPair]]:
    return sorted(groups, key=lambda group: statement(group[0], token).lower())


def listing(groups: list[list[MemoryPair]], token: str) -> str:
    return "\n\n".join(f"[M{mark}]\nUser: {statement(group[0], token)}" for mark, group in enumerate(groups, start=1))


def sequence_from(reply: str, groups: list[list[MemoryPair]]) -> list[list[MemoryPair]]:
    # The reply runs from the last written note to the first; a note it leaves out goes before every placed one.
    marks = [int(mark) for mark in MARK_RE.findall(reply)]
    chosen = [groups[mark - 1] for mark in dict.fromkeys(marks) if 1 <= mark <= len(groups)]
    return [group for group in groups if group not in chosen] + chosen[::-1]


def record_block(mark: int, pair: MemoryPair) -> str:
    head = f"[M{mark}] {pair.timestamp[:10]}" if pair.timestamp else f"[M{mark}]"
    return f"{head}\nUser: {pair.prompt}\nAssistant: {pair.response}"


def grouped_view(groups: list[list[MemoryPair]]) -> str:
    blocks: list[str] = []
    mark = 0
    for group in groups:
        lines = []
        for pair in group:
            mark += 1
            lines.append(record_block(mark, pair))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


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


def filed_view(notes: list[MemoryPair]) -> str:
    """Each note with its filing date and time, in the order given."""
    return "\n\n".join(f"[M{mark}] {pair.timestamp[:16].replace('T', ' ')}\nUser: {pair.prompt}\nAssistant: {pair.response}" if pair.timestamp
                       else f"[M{mark}]\nUser: {pair.prompt}\nAssistant: {pair.response}" for mark, pair in enumerate(notes, start=1))


def lead_view(groups: list[list[MemoryPair]], token: str, header: str = LEAD_HEADER) -> str:
    statements = [statement(group[0], token) for group in groups]
    if len(statements) < 2 or any(len(text) > LEAD_MAX_STATEMENT_CHARS for text in statements):
        return ""
    return header + "\n" + "\n".join(f"{mark}. {text}" for mark, text in enumerate(statements, start=1))


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome) -> bool:
    if deadline - time.monotonic() < MIN_SECONDS:
        outcome.events.append("deciding call: no time left")
        return False
    await engine.converse(req, messages, None, effort, max_tokens, deadline, outcome, checkable=True)
    return bool(outcome.content.strip())


class ShortPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, readings: dict[str, asyncio.Future[str | None]] | None = None, order_max_tokens: int = ORDER_MAX_TOKENS, full_dates: bool = False) -> None:
        self.engine = engine
        self.llm = engine.llm
        self.tally = engine.tally
        self.readings = readings
        self.effort = effort
        self.max_tokens = max_tokens
        self.full_dates = full_dates
        self.order_max_tokens = order_max_tokens

    async def call(self, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, deadline: float, outcome: Outcome, what: str) -> str | None:
        return await consult(self.llm, self.tally, req, messages, max_tokens, self.effort, deadline, outcome, what)

    async def read_state(self, req: RunRequest, filed: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        """One reading of the filed notes alone (no message): where things stand after every note."""
        if len(filed) < 2:
            return ""
        messages = [{"role": "system", "content": short_system(req.system_prompt, STATE_SYSTEM)}, {"role": "user", "content": STATE_BRIEF.format(notes=filed_view(filed))}]
        reply = await self.shared_state(req, messages, deadline, outcome)
        written = (reply or "").strip()
        outcome.events.append(f"state reading: {len(written.splitlines())} lines sha={hashlib.sha256(written.encode()).hexdigest()[:10]}" if written else "state reading: none")
        return written

    async def read_order(self, req: RunRequest, messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> str | None:
        readings = self.readings
        key = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest() if readings is not None else ""
        held = readings.get(key) if readings is not None else None
        if held is not None:
            outcome.events.append("order pass: the same notes were already read in this run")
            return await asyncio.shield(held)
        if readings is not None:
            held = asyncio.get_running_loop().create_future()
            readings[key] = held
            while len(readings) > READINGS_HELD:
                del readings[next(iter(readings))]
        reply: str | None = None
        try:
            reply = await self.call(req, messages, self.order_max_tokens, deadline, outcome, "order pass")
        finally:
            if readings is not None and held is not None:
                if reply is None:
                    readings.pop(key, None)
                held.set_result(reply)
        return reply

    async def shared_state(self, req: RunRequest, messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> str | None:
        """The state reading for this user's system text and filed notes, read once per process (the message is not part
        of its input); a request that finds it still being written waits within its own deadline."""
        readings = self.readings
        if readings is None:
            return await self.call(req, messages, self.order_max_tokens, deadline, outcome, "state reading")
        key = hashlib.sha256(json.dumps([normalize_user_id(req.user_id), messages], sort_keys=True).encode()).hexdigest()
        held = readings.get(key)
        if held is not None:
            outcome.events.append("state reading: the same notes were already read for this user")
            try:
                return await asyncio.wait_for(asyncio.shield(held), max(0.01, deadline - time.monotonic() - STATE_WAIT_RESERVE))
            except asyncio.TimeoutError:
                outcome.events.append("state reading: the earlier reading was not ready in time")
                return None
        held = asyncio.get_running_loop().create_future()
        readings[key] = held
        while len(readings) > READINGS_HELD:
            del readings[next(iter(readings))]
        reply: str | None = None
        try:
            reply = await self.call(req, messages, self.order_max_tokens, deadline, outcome, "state reading")
        finally:
            if reply is None:
                readings.pop(key, None)
            held.set_result(reply)
        return reply

    async def groups(self, req: RunRequest, records: list[MemoryPair], token: str, deadline: float, outcome: Outcome) -> list[list[MemoryPair]] | None:
        groups = by_statement(records, token)
        if len(groups) < 2:
            return groups
        shuffled = by_text(groups, token)
        messages = [{"role": "system", "content": short_system(req.system_prompt, ORDER_SYSTEM)}, {"role": "user", "content": ORDER_BRIEF.format(notes=listing(shuffled, token))}]
        reply = await self.read_order(req, messages, deadline, outcome)
        if reply is None:
            return None
        outcome.events.append(f"order pass: {first_line(reply)}")
        return sequence_from(reply, shuffled)

    async def answer(self, req: RunRequest, records: list[MemoryPair], token: str, deadline: float, outcome: Outcome) -> bool:
        filed = one_copy(sorted(records, key=lambda p: (p.timestamp, p.pair_id)), token)
        groups = [[pair] for pair in filed]
        notes = filed_view(filed)
        lead = lead_view(groups, token, FILED_HEADER)
        opening = f"{lead}\n\n" if lead else ""
        state = await self.read_state(req, filed, deadline, outcome)
        beside = f"\n\n{STATE_HEADER}\n{state}" if state else ""
        system = short_system(req.system_prompt, DATED_PROGRAM_SYSTEM if self.full_dates else PROGRAM_SYSTEM)
        shown = f"{opening}{NOTES_HEADER}\n\n{notes}{beside}"
        asked = SPACE.sub(" ", asked_part(req.user_input)).strip()
        key = "reply:" + hashlib.sha256(json.dumps([normalize_user_id(req.user_id), system, shown, question_kind(asked)]).encode()).hexdigest()
        earlier, held = await self.earlier_reply(key, deadline, outcome)
        draft = f"\n\n{EARLIER_REPLY_NOTE.format(asked=earlier[0], reply=earlier[1])}" if earlier is not None else ""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": f"{shown}{draft}\n\n{MESSAGE_HEADER}\n{req.user_input}\n\n{HOST_NOTE} {PROGRAM_NOTE}"}]
        outcome.events.append(f"short path records={len(records)} shown={len(filed)} in filing order")
        if held is None:
            return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)
        decided = False
        try:
            decided = await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)
        finally:
            reply = outcome.content.strip()[:EARLIER_REPLY_CHARS] if decided else ""
            if not reply and self.readings is not None and self.readings.get(key) is held:
                del self.readings[key]
            held.set_result((asked, reply) if reply else None)
        return decided

    async def earlier_reply(self, key: str, deadline: float, outcome: Outcome) -> tuple[tuple[str, str] | None, asyncio.Future[Any] | None]:
        """The reply an earlier request with this key shipped (its asked sentence and reply), waited for within this
        request's deadline; or, for the first request with the key, the future its own reply will fill."""
        replies = self.readings
        if replies is None:
            return None, None
        held = replies.get(key)
        if held is not None:
            try:
                left = deadline - time.monotonic()
                # Stop waiting with time left to decide alone: up to 90 s before the deadline, or about one typical
                # deciding call when less is left, and never later than STATE_WAIT_RESERVE before the deadline.
                wait = min(max(EARLIER_REPLY_WAIT, left - EARLIER_REPLY_RESERVE), left - STATE_WAIT_RESERVE)
                earlier = await asyncio.wait_for(asyncio.shield(held), max(0.01, wait))
            except asyncio.TimeoutError:
                outcome.events.append("earlier reply: not ready in time")
                return None, None
            outcome.events.append("earlier reply: shown" if earlier is not None else "earlier reply: none")
            return earlier, None
        held = asyncio.get_running_loop().create_future()
        replies[key] = held
        while len(replies) > READINGS_HELD:
            del replies[next(iter(replies))]
        return None, held


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


def latest_handover(passages: list[tuple[str, str]], pairs: list[MemoryPair]) -> tuple[str, str] | None:
    """The most recent passage with handover wording that names a person the notes know by full name."""
    return next((passage for passage in reversed(passages) if HANDOVER_CUE_RE.search(passage[1]) and full_names(passage[1], pairs)), None)


def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, next_step: bool = False, holder: bool = False, status: bool = False) -> list[tuple[str, str]]:
    passages = dated_passages(notes, excerpts, labels)
    if not passages:
        return []
    others = other_paragraphs(notes, pairs)
    misspelt: dict[tuple[str, str], bool] = {}
    kept = [passage for passage in passages if not recurs(passage_shape(passage[1], phrase), others, misspelt)] or passages
    last = kept[-1]
    picks = [(RECENT_LINE, f"{last[0]} {last[1]}")]
    handed = latest_handover(passages, pairs) if holder else None
    if handed is not None:
        if handed is not last:
            picks.append((RECENT_HOLDER_LINE, f"{handed[0]} {handed[1]}"))
        return picks
    # A state question: a passage that names a person gives someone a task, not the state; it is not picked out.
    named = None if status else next((passage for passage in reversed(kept) if full_names(passage[1], pairs)), None)
    if named is not None and named is not last:
        picks.append((RECENT_PERSON_LINE, f"{named[0]} {named[1]}"))
    if next_step:
        pointed = next((passage for passage in reversed(passages) if ACTION_CUE_RE.search(passage[1]) and FULL_NAME_RE.search(passage[1])), None)
        if pointed is not None:
            picks.append((RECENT_ACTION_LINE, f"{pointed[0]} {pointed[1]}"))
    return picks


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, message: str = "") -> str:
    kind = question_kind(message) if message else ""
    picks = recent_picks(notes, excerpts, phrase, pairs, labels, next_step=kind == "next", holder=kind in HOLDER_KINDS, status=kind in STATE_KINDS)
    if not picks:
        return ""
    return RECENT_HEADER + "\n" + "\n".join(line.format(phrase=phrase, passage=passage) for line, passage in picks)


def drafted(reply: str | None) -> bool:
    return bool(parse_slot(reply or "")[1])


class TopicPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, max_chars: int, draft: bool = False) -> None:
        self.engine = engine
        self.effort = effort
        self.max_tokens = max_tokens
        self.max_chars = max_chars
        self.draft = draft

    def fits(self, notes: list[MemoryPair]) -> bool:
        return sum(record_size(pair) for pair in notes) <= self.max_chars

    def with_cards(self, notes: list[MemoryPair], pairs: list[MemoryPair], named: list[str] | None = None) -> list[MemoryPair]:
        if not named:
            text = "\n".join(pair.prompt + "\n" + pair.response for pair in notes)
            named = list(dict.fromkeys(full_names(text, pairs) + named_by_alias(text, pairs)))
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
        people = ""
        if asks_contact(req.user_input):
            named = await self.named_in_reading(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
            if not named:
                text = "\n".join(pair.prompt + "\n" + pair.response for pair in notes)
                named = list(dict.fromkeys(full_names(text, pairs) + named_by_alias(text, pairs)))
            if question_kind(req.user_input) in HOLDER_KINDS:
                handed = latest_handover(dated_passages(notes, found.excerpts), pairs)
                if handed is not None:
                    named = list(dict.fromkeys(named + full_names(handed[1], pairs)))
            notes = self.with_cards(notes, pairs, named)
            people = person_index(named, notes, pairs)
            if people:
                outcome.events.append(f"person index {people.count(chr(10))}")
        draft = await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome) if self.draft and question_kind(req.user_input) not in HOLDER_KINDS else ""
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft, people)
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        picks = recent_picks(notes, excerpts, phrase, pairs, status=question_kind(req.user_input) in STATE_KINDS)
        if not picks:
            return ""
        messages = [{"role": "system", "content": short_system(req.system_prompt, LATEST_SYSTEM)}, {"role": "user", "content": LATEST_BRIEF.format(passages="\n".join(passage for _, passage in picks), message=req.user_input + (f"\n\n{answer_hint(req.user_input)}" if answer_hint(req.user_input) else ""))}]
        reply = await consult(self.engine.llm, self.engine.tally, req, messages, self.max_tokens, self.effort, deadline, outcome, "latest passages reading")
        written = drafted(reply)
        outcome.events.append(f"latest passages reading: {'draft' if written else 'no draft'}")
        return (reply or "").strip() if written else ""

    async def named_in_reading(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> list[str] | None:
        reply = await consult(self.engine.llm, self.engine.tally, req, topic_messages(req, notes, excerpts, phrase, pairs) + [{"role": "user", "content": PERSON_BRIEF}], self.max_tokens, self.effort, deadline, outcome, "thread reading")
        answer = SPACE.sub(" ", reply or "")
        named = list(dict.fromkeys(full_names(answer, pairs) + named_by_alias(answer, pairs)))
        outcome.events.append(f"thread reading named {len(named)}")
        return named or None


PEOPLE_HEADER = ("People the notes name (each line gives the notes about that person, found by their full name or by a "
                 "nickname a note gives them; a note that names someone only by a nickname is about the person that "
                 "nickname belongs to):")


def person_index(named: list[str], notes: list[MemoryPair], pairs: list[MemoryPair]) -> str:
    """For each named person: the nicknames the notes give them and the marks of the notes in their card."""
    seat = {pair.pair_id: mark for mark, pair in enumerate(notes, start=1)}
    lines = []
    for name in named:
        card = person_card(name, pairs)
        marks = sorted({seat[pair.pair_id] for pair in card if pair.pair_id in seat})
        if not marks:
            continue
        parts = set(name.split())
        aliases = sorted({alias for pair in card if name in pair.prompt for alias in ALIAS_RE.findall(pair.prompt) if alias not in parts})
        called = f" (called {', '.join(aliases)})" if aliases else ""
        lines.append(f"- {name}{called}: " + ", ".join(f"M{mark}" for mark in marks))
    return PEOPLE_HEADER + "\n" + "\n".join(lines) if lines else ""


CONTACT_WORDS = ("email", "emails", "address", "addresses")


def asks_contact(message: str) -> bool:
    """The contact pattern, or a word one edit off email or address (a misspelt contact question)."""
    if CONTACT_RE.search(message):
        return True
    return any(within_one_edit(word, cue) for word in re.findall(r"[a-z]{5,}", message.lower()) for cue in CONTACT_WORDS)


def topic_messages(req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], draft: str = "", people: str = "") -> list[dict[str, Any]]:
    recent = recent_view(notes, excerpts, phrase, pairs, message=req.user_input)
    beside = f"\n\n{recent}" if recent else ""
    after = f"\n\n{DRAFT_NOTE.format(draft=draft)}" if draft else ""
    hint = answer_hint(req.user_input)
    index = f"\n\n{people}" if people else ""
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{index}{beside}{after}\n\n{MESSAGE_HEADER}\n{req.user_input}" + (f"\n\n{hint}" if hint else "")
    return [{"role": "system", "content": short_system(req.system_prompt, TOPIC_SYSTEM)}, {"role": "user", "content": user}]


@dataclass(frozen=True)
class TopicNotes:
    topic: Topic
    notes: list[MemoryPair]
    excerpts: dict[str, str]


def find_topic(question: str, pairs: list[MemoryPair], min_density: int, max_chars: int) -> TopicNotes | None:
    if not pairs or QUOTE_RE.search(question) or full_names(question, pairs):
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
    recent = recent_view(found.notes, found.excerpts, phrase, pairs, labels, message=question)
    return whole, passages_view(found.notes, found.excerpts, phrase, labels) + (f"\n\n{recent}" if recent else "")


def nicknames(pairs: list[MemoryPair]) -> set[str]:
    return {alias for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS for alias in ALIAS_RE.findall(pair.prompt)}


def alias_names(pairs: list[MemoryPair]) -> dict[str, str]:
    """Nickname to full name, from each short record that introduces a quoted alias beside exactly one full name."""
    out: dict[str, str] = {}
    for pair in pairs:
        if len(pair.prompt) >= SHORT_RECORD_CHARS:
            continue
        names = list(dict.fromkeys(FULL_NAME_RE.findall(pair.prompt)))
        if len(names) != 1:
            continue
        for alias in ALIAS_RE.findall(pair.prompt):
            if alias not in names[0].split():
                out.setdefault(alias, names[0])
    return out


def named_by_alias(text: str, pairs: list[MemoryPair]) -> list[str]:
    """The full names of the people a text names by nickname."""
    return [name for alias, name in alias_names(pairs).items() if re.search(r"\b" + re.escape(alias) + r"\b", text)]


def thread_of(question: str, notes: list[MemoryPair], pairs: list[MemoryPair]) -> list[MemoryPair]:
    patterns = [re.compile(r"\b" + re.escape(nick) + r"\b") for nick in sorted(nicknames(pairs)) if re.search(r"\b" + re.escape(nick) + r"\b", question)]
    if not patterns:
        return notes
    nicks = [nick for nick in sorted(nicknames(pairs)) if len(nick) >= 4 and re.search(r"\b" + re.escape(nick) + r"\b", question)]
    slipped = lambda text: any(within_one_edit(word.lower(), nick.lower()) for nick in nicks for word in re.findall(r"\b[A-Z][a-z]+\b", text))
    thread = [pair for pair in notes if any(pattern.search(pair.prompt) for pattern in patterns) or slipped(pair.prompt)]
    if sum(1 for pair in thread if PARAGRAPH_BREAK in pair.prompt) < MIN_THREAD_NOTES:
        return notes
    return thread
