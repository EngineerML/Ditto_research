from __future__ import annotations

import difflib

import asyncio
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
from .answer import parse_slot
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, asked_part, identifier_tokens, tokens
from .memory.people import person_card, ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS, by_date, cards_for, full_names
from .memory.topic import Topic, TopicIndex, paragraphs, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_ANSWER_LINE = "Reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
PROGRAM_SYSTEM = f"{SHORT_OPENING} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year, even when the message asks for less. If the notes do not state it, say so."
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year. If the notes do not state it, say so."
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MIN_SECONDS = 8.0
DRAFTS_HELD = 512
DRAFT_KEY_OVERLAP = 0.7  # a rewording whose asked words overlap a held draft's by this share (Jaccard) over the same notes reuses that draft: the misspelt words of one rewording must not split its group
DRAFT_WORD_RE = re.compile(r"[a-z0-9]+")
DRAFT_KEYS: dict[str, list[tuple[frozenset[str], str]]] = {}  # base (user, system, notes) -> [(asked words, key)]
DRAFT_CHECK_MIN_SECONDS = 45.0
DRAFT_CHECK_BRIEF = "Before this draft is used, check it against the entries above, read oldest first with the reading rules: for each entry decide whether it sets a value, only proposes one, declines a proposal, undoes an earlier entry, reverts to the previous entry, or is unrelated, keep track of the value in place after each entry (after A, then B, then C, an entry that reverts to the previous entry puts B back in place), and then what holds at the end of the sequence. If the draft's value is what holds, write the draft out again unchanged. If not, write the reply again with the value that holds, in the same form: briefly, ending with the line 'ANSWER: <value>'. If the entries do not state what the question asks, say so in one sentence, with no ANSWER line. Write only the reply, nothing about the check."
SHARED_DRAFT_EFFORT = "medium"  # at high effort this model reasoned to the 32000-token limit and returned no text
SHARED_DRAFT_MAX_TOKENS = 16000  # room for a long chain of statements
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
STORY_NOTE_PARAGRAPHS = 6
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
FILED_LEAD_HEADER = "The statements of the notes below, oldest first, each after the day its note was filed:"
CHAIN_NOTE = "The notes are listed oldest first by the day each was filed, the order they were written in. Read them in that order as one sequence before answering. A later note can change a value or bring an earlier one back. A note saying that an earlier entry was a mistake, wrong or struck undoes that entry entirely, together with anything it said about the entries before it, so what held before that entry holds again; a suggested change holds only once a note says it went ahead, and one turned down changes nothing. What holds now is what the whole sequence leaves in place. A note that only asks for or proposes a change (an update requested, a value to become another) does not make it: the value changes only once a later note says the change went ahead, and a note saying the request was dropped or declined leaves the value as it was. A note that says the value reverts to the previous entry sets it back to what held before the latest change. A step is closed once a note says it is done, confirmed, dropped or closed, and open again when a later note says it failed its check, was reopened or is open again; the earliest open step is the first in the planned order that the notes leave open. Where a note itself says on what day something happened or took effect, that day, not its filing day, places it in time. Give the value that holds now once, on its own: not the earlier values, not the steps that led to it, and not the sentence of the note that set it. Who holds or owns something after every recorded handover or reassignment is one person, the one the last handover left it with — when it went to A, A handed it to B and B handed it to C, the answer is C alone; 'after every recorded handover' means after all of them, not one name per handover — and the ANSWER line holds that one name, never the chain of holders."
LEAD_MAX_STATEMENT_CHARS = 1000
PROGRAM_MAX_RECORD_CHARS = 2000
PERSON_BRIEF = "Before the message is answered: which person is it asking about? Reply with that person's full name as the notes give it, and nothing else."
RECENT_HEADER = "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:"
RECENT_LINE = "- The most recent passage about “{phrase}”: {passage}"
RECENT_HANDOVER_LINE = "- The most recent passage about “{phrase}” that puts a person in charge of it: {passage}"
HANDOVER_RE = re.compile(r"\b(?:handed (?:over )?to|handed \w+ (?:\w+ )?to|passed [^.;]{0,40}\bto\b|picked up [^.;]{0,40}\bfrom\b|is the owner|owner now|now owns|ownership of|'s now|in charge|to run\b|holding the thread|the handoff|run point|took it on|the one accountable|owning|a name on it)", re.IGNORECASE)
RECENT_ACTION_LINE = "- The most recent passage about “{phrase}” that gives a next action to a person: {passage}"
ACTION_CUE_RE = re.compile(r"\b(?:next step|next move|next from them|first action from|follow-up for|open action|is waiting on|the ball is with|agreed to|is going to|will \w+|would \w+|next on)\b", re.IGNORECASE)
RECENT_PERSON_LINE = "- The most recent passage about “{phrase}” that names a person: {passage}"
RECENT_NOTE_LINE = "- The last passage about “{phrase}” in one of the two latest notes about it: {passage}"
RECUR_SHARE = 0.8
RECUR_EXTRA_WORDS = 6
RECUR_TIMES = 2
RECUR_MAX_WORDS = 40
RECUR_TYPO_WORD = 4
LATEST_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
LATEST_BRIEF = "Passages:\n{passages}\n\nMessage:\n{message}"
HOLDER_DRAFT_SYSTEM = "The message asks who owns or holds the work now. The passages below are the latest passage about it and the latest passage that seems to put a person in charge of it. A later note that only gives someone a next step, names a vendor or reports its state does not change who owns it. End with the line 'ANSWER: <that person's full name>'."
DISAGREE_DRAFT_SYSTEM = "The message asks whether the notes agree on where it stands, and the passages below are what the two latest notes say of its state. Reply with the state each of them gives, as the one or two words that passage uses for it, and say that the records disagree where the two differ; states that earlier notes gave it, and its people, figures and vendors, are not asked. End with the line 'ANSWER: <state in the earlier passage> ; <state in the later passage> ; disagree'."
SHARED_DRAFT_NOTE = "A draft reply, written once from these same notes for the question \"{asked}\"; it has not been checked, and the notes decide wherever they differ:\n{draft}\n\nReply with the draft as it stands, word for word, whatever your own reading of the notes; a draft that declines stands as it is. Give the value or values the question asks for as the draft gives them, with no other value beside them."
SHARED_WAIT_RESERVE = 60.0
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


def record_block(mark: int, pair: MemoryPair) -> str:
    head = f"[M{mark}] {pair.timestamp[:10]}" if pair.timestamp else f"[M{mark}]"
    return f"{head}\nUser: {pair.prompt}\nAssistant: {pair.response}"


SAME_ASKED_RATIO = 0.9
SAME_NOTES_SHARE = 0.99
SAME_REPLY_MAX_TOKENS = 1200
SAME_REPLY_TRIES = 2
SAME_REPLY_NO = re.compile(r"\W*different\W*$", re.IGNORECASE)
SAME_WORDS_LINE = "Code found almost the same words and figures in the notes behind the two messages, so they may hold the same facts here. This compares words; it does not read them, and it is not checked."
SAME_REPLY_BRIEF = "The earlier question:\n{question}\n\nYour reply to it:\n{reply}\n\nNew message:\n{message}"
SAME_REPLY_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are a question about one of the user's case files, the reply you gave to it, and a new message that code matched to that question over the same notes; code may be wrong. Other opening or closing words about how to read the file, another way of asking and slips of the keyboard do not make it another question. Keep to your reply and do not work the answer out again: if the new message asks for the same thing, send your reply again, word for word, ending with its ANSWER line. Reply with only the word DIFFERENT if the new message names another step, id or subject, asks for another value, or asks you to look it up again."


def same_asked(asked: str, seen: str) -> bool:
    return difflib.SequenceMatcher(None, asked, seen).ratio() >= SAME_ASKED_RATIO


def note_words(records: list[MemoryPair], token: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9][a-z0-9.@-]*", " ".join(pair.prompt for pair in records).lower())) - {token}


def codes_asked(asked: str, token: str) -> frozenset[str]:
    return frozenset(found for found in re.findall(r"[a-z0-9-]*\d[a-z0-9-]*", asked.lower()) if found != token)


def same_notes(words: frozenset[str], seen: frozenset[str]) -> bool:
    return len(words & seen) >= SAME_NOTES_SHARE * len(words | seen)


async def repeat_reply(engine: RecordsEngine, req: RunRequest, question: str, earlier: str, deadline: float, outcome: Outcome) -> bool:
    """The model sees its earlier reply and the new message, and sends the reply again or says the message asks something else. Whatever it writes ships, except that word alone, which decides the request as usual."""
    messages = [{"role": "system", "content": short_system(req.system_prompt, SAME_REPLY_SYSTEM)}, {"role": "user", "content": SAME_WORDS_LINE + "\n\n" + SAME_REPLY_BRIEF.format(question=question, reply=earlier, message=req.user_input)}]
    reply = ""
    for _ in range(SAME_REPLY_TRIES):
        try:
            result = await engine.llm.chat(messages, None, deadline=deadline, max_tokens=SAME_REPLY_MAX_TOKENS, reasoning_effort="low")
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
    if not reply or SAME_REPLY_NO.match(reply):
        outcome.events.append("same question: decided anew")
        return False
    outcome.content = reply
    outcome.answer = parse_slot(reply)[1]
    outcome.events.append("same question: earlier reply sent again")
    return True


async def consult(llm: LLM, tally: TokenTally, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, effort: str, deadline: float, outcome: Outcome, what: str, whole: bool = False) -> str | None:
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
        if result.content.strip() and not (whole and result.finish_reason == "length"):
            return result.content
        outcome.events.append(f"{what} empty reply finish={result.finish_reason} effort={level}")
    return None


def short_system(operator: str, own: str) -> str:
    if not operator.strip():
        return own
    return own + "\n\n" + OPERATOR_SEAM + "\n" + operator.strip()


LEAD_SAME_STATEMENT = 0.88


def same_statement(a: str, b: str) -> bool:
    """Two statements of one entry — the calendar entry, the forwarded text and the fridge-list line say the same thing, each with its own misspellings."""
    x, y = " ".join(a.lower().split()), " ".join(b.lower().split())
    return x == y or difflib.SequenceMatcher(None, x, y).ratio() >= LEAD_SAME_STATEMENT




def filed_lead(notes: list[MemoryPair], token: str) -> str:
    statements = [statement(pair, token) for pair in notes]
    if len(statements) < 2 or any(len(text) > LEAD_MAX_STATEMENT_CHARS for text in statements):
        return ""
    # One line per entry: notes filed the same day that state the same thing (each copy with its own misspellings) are one statement, shown once.
    merged: list[tuple[MemoryPair, str]] = []
    for pair, text in zip(notes, statements):
        if not (merged and merged[-1][0].timestamp[:10] == pair.timestamp[:10] and same_statement(merged[-1][1], text)):
            merged.append((pair, text))
    return FILED_LEAD_HEADER + "\n" + "\n".join(f"{mark}. {pair.timestamp[:10]}: {text}" if pair.timestamp else f"{mark}. {text}" for mark, (pair, text) in enumerate(merged, start=1))


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome, checkable: bool = True) -> bool:
    if deadline - time.monotonic() < MIN_SECONDS:
        outcome.events.append("deciding call: no time left")
        return False
    start = len(messages)
    await engine.converse(req, messages, None, effort, max_tokens, deadline, outcome, checkable=checkable)
    if outcome.content.strip():
        return True
    engine.carried.extend(made_calls(messages[start:]))
    return False


def made_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("role") == "tool" or (message.get("role") == "assistant" and message.get("tool_calls"))]


READING_RULES = """Reading the entries, oldest first, before answering:
- a later entry that sets a value replaces the earlier one; "the newest entry governs";
- an entry that only proposes or requests a change makes none, and an entry saying the change did not go ahead, was declined or dropped leaves the value as it was: the answer is then the value that already held (when the decision was A and a proposal to change it to B did not go ahead, the answer is A, not the sentence about the proposal);
- an entry saying an earlier entry was a mistake, wrong or struck undoes that entry entirely, so what held before it holds again;
- an entry saying the value reverts to the previous entry sets it back to the value that held before the latest change: when it was A, then B, then C, "reverts to the previous entry" makes it B again — the value before the latest change, not the latest entry's own value; it counts back from the latest change only, so the words "the newest entry governs" in that same entry do not keep the latest value in place;
- who holds or owns something after every recorded handover is the one person the last handover left it with (A to B to C gives C), one name;
- a step is closed once an entry says it is done or confirmed, and open again when a later entry reopens it.
- the same value may be written differently in different entries (19:35 and 7:35 pm, 2026-02-04 and 4 February 2026, $1,200 and 1200 dollars): an entry that strikes or replaces "7:35 pm" strikes or replaces the entry that set 19:35;
- where the entries name people by a handle (such as @oak-17) and a directory entry says whose handle it is, a question for the person, their name or who holds a role is answered with the person's name, not the handle; a question for the contact or handle is answered with the handle.
- a list changes one item at a time: an entry that takes an item off removes only that item, one that puts an item on adds only that item, and one that swaps A for B removes A and adds B; the full current list is the first list with every such change applied in order, and a change that a later entry scratches or calls a mistake is undone (the item it removed is back, the item it added is gone);
- where the question asks what held on a given date ("On 15 June 2024, which …", "as of …"), the answer is the value set by the latest change that took effect on or before that date, going by the date each entry gives for its change ("from 22 June 2024", "with effect from May 8, 2024", "on 2024-06-03"), not by the day the entry was filed: a change that takes effect after that date does not count for it, so the value that held before that later change is the answer;
The value asked for is what the whole sequence leaves in place on the date the question names, or now when it names none, given once, on its own."""


def program_messages(system: str, shown: str, note: str, message: str) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": f"{shown}\n\n{READING_RULES}\n\n{note}{MESSAGE_HEADER}\n{message}"}]


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
        notes = by_date(records)
        lead = filed_lead(notes, token)
        opening = f"{lead}\n\n" if lead else ""
        system = short_system(req.system_prompt, " ".join([PROGRAM_SYSTEM, CHAIN_NOTE, *guide_records.program_notes(req.user_input)]))
        shown = f"{opening}{NOTES_HEADER}\n\n{record_view(notes)}"
        asked = asked_part(req.user_input)
        key = self.draft_key(normalize_user_id(req.user_id), system, shown, asked)
        draft = await self.shared_draft(req, key, program_messages(system, shown, "", asked), deadline, outcome)
        note = SHARED_DRAFT_NOTE.format(asked=asked, draft=draft.strip()) + "\n\n" if draft is not None else ""
        outcome.events.append(f"short path records={len(records)}{' shared draft' if note else ''}")
        # with a shared draft in hand the final check FC is not asked: it was the pass that turned a right shared value into another for one rewording of three.
        return await decide(self.engine, req, program_messages(system, shown, note, req.user_input), self.effort, self.max_tokens, deadline, outcome, checkable=not note)

    def draft_key(self, user: str, system: str, shown: str, asked: str) -> str:
        """One key per question over the same notes: a held draft whose asked words overlap this rewording's by DRAFT_KEY_OVERLAP is the same question, however its words are misspelt."""
        base = hashlib.sha256(json.dumps([user, system, shown]).encode()).hexdigest()
        words = frozenset(DRAFT_WORD_RE.findall(asked.lower()))
        held = DRAFT_KEYS.setdefault(base, [])
        for other, key in held:
            if key in self.drafts and words and other and len(words & other) / len(words | other) >= DRAFT_KEY_OVERLAP:
                return key
        key = hashlib.sha256(json.dumps([user, system, shown, asked]).encode()).hexdigest()
        held.append((words, key))
        if len(DRAFT_KEYS) > DRAFTS_HELD:
            del DRAFT_KEYS[next(iter(DRAFT_KEYS))]
        return key

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
        while len(self.drafts) > DRAFTS_HELD:
            del self.drafts[next(iter(self.drafts))]
        draft: str | None = None
        try:
            reply = await consult(self.llm, self.tally, req, messages, max(self.max_tokens, SHARED_DRAFT_MAX_TOKENS), SHARED_DRAFT_EFFORT, deadline, outcome, "shared draft")
            if reply and reply.strip():
                draft = reply  # a reply without an ANSWER line (a decline) is shared too: every rewording then declines alike
                # A second reading checks the draft against the entries with the reading rules; its reply is the draft.
                if drafted(reply) and deadline - time.monotonic() > DRAFT_CHECK_MIN_SECONDS:
                    check = await consult(self.llm, self.tally, req, messages + [{"role": "assistant", "content": reply}, {"role": "user", "content": DRAFT_CHECK_BRIEF}], max(self.max_tokens, SHARED_DRAFT_MAX_TOKENS), SHARED_DRAFT_EFFORT, deadline, outcome, "draft check", whole=True)
                    if check and check.strip():
                        # The check is the designated critic: whatever text it writes is the draft, a decline included; only a check with no text leaves the first draft
                        draft = check
                        outcome.events.append("draft check: the check's reply is the draft")
                    else:
                        outcome.events.append("draft check: no reply, the first draft stands")
        finally:
            if draft is None and self.drafts.get(key) is held:
                del self.drafts[key]
            held.set_result(draft)
        outcome.events.append("shared draft: written here" if draft is not None else "shared draft: none written")
        return draft


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


# The notes carry the same one-letter misspellings as the messages ("the handovr", "is the ownr now"): a cue word is read for the word it stands
# for before the fixed passage patterns below are applied. Only the host's choice of passage to pick depends on it; the notes are shown as written.
PASSAGE_WORDS = ("owner", "owns", "owning", "handoff", "handed", "passed", "picked", "took", "charge", "running", "holding", "accountable", "next", "step", "action", "open", "moved", "started", "opening", "rebooked", "switched", "replaced", "vendor", "supplier")


def _passage_variants() -> dict[str, str]:
    seen: dict[str, str | None] = {}
    for word in PASSAGE_WORDS:
        for variant in guide_records._variants(word):
            if variant in PASSAGE_WORDS or variant in guide_records._KEYWORDS:
                continue
            seen[variant] = None if variant in seen and seen[variant] != word else word
    return {variant: word for variant, word in seen.items() if word}


_PASSAGE_VARIANTS = _passage_variants()
_PASSAGE_WORD_RE = re.compile(r"[A-Za-z]+")


def passage_plain(text: str) -> str:
    return _PASSAGE_WORD_RE.sub(lambda m: _PASSAGE_VARIANTS.get(m.group(0).lower(), m.group(0)), text)




def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False, order: bool = False, figure: bool = False) -> list[tuple[str, str]]:
    passages = dated_passages(notes, excerpts, labels)
    if not passages:
        return []
    others = other_paragraphs(notes, pairs)
    misspelt: dict[tuple[str, str], bool] = {}
    if agreement:
        latest = last_in_latest_notes(notes, excerpts, phrase, others, misspelt, labels)
        if len(latest) == 2:
            return [(RECENT_NOTE_LINE, passage) for passage in latest]
    kept = [passage for passage in passages if not recurs(passage_shape(passage[1], phrase), others, misspelt)] or passages
    last = kept[-1]
    picks = [(RECENT_LINE, f"{last[0]} {last[1]}")]
    if holder:
        handed = latest_handover(notes, excerpts, labels)
        if handed is not None:
            picks.append((RECENT_HANDOVER_LINE, f"{handed[0]} {handed[1]}"))
        return picks
    if next_step:
        acting = next((passage for passage in reversed(passages) if ACTION_CUE_RE.search(passage_plain(passage[1])) and FULL_NAME_RE.search(passage[1])), None)
        if acting is not None:
            picks.append((RECENT_ACTION_LINE, f"{acting[0]} {acting[1]}"))
            return picks
    if status or order:
        return picks
    named = next((passage for passage in reversed(kept) if full_names(passage[1], pairs)), None)
    if named is not None and named is not last:
        picks.append((RECENT_PERSON_LINE, f"{named[0]} {named[1]}"))
    return picks


def last_in_latest_notes(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, others: Counter[frozenset[str]], misspelt: dict[tuple[str, str], bool], labels: dict[str, str] | None = None) -> list[str]:
    out: list[str] = []
    for mark, pair in reversed(list(enumerate(notes, start=1))):
        if pair.pair_id not in excerpts:
            continue
        kept = [paragraph for paragraph in paragraphs(excerpts[pair.pair_id]) if not recurs(passage_shape(paragraph, phrase), others, misspelt)]
        if kept:
            out.append(f"{passage_head(mark, pair, labels)} {kept[-1]}")
        if len(out) == 2:
            break
    return out


def latest_handover(notes: list[MemoryPair], excerpts: dict[str, str], labels: dict[str, str] | None = None) -> tuple[str, str] | None:
    return next((passage for passage in reversed(dated_passages(notes, excerpts, labels)) if HANDOVER_RE.search(passage_plain(passage[1])) and FULL_NAME_RE.search(passage[1])), None)


def handover_names(notes: list[MemoryPair], excerpts: dict[str, str], pairs: list[MemoryPair]) -> list[str]:
    handed = latest_handover(notes, excerpts)
    return full_names(handed[1], pairs) if handed is not None else []


CONTACT_HEADER = "Picked out by code, not checked — the notes above decide wherever they differ: the short notes about the person the latest handover put in charge, by their full name and by the nickname a note gives them:"


def contact_view(notes: list[MemoryPair], excerpts: dict[str, str], pairs: list[MemoryPair]) -> str:
    lines: list[str] = []
    held = {pair.pair_id: pair for pair in notes}
    for name in handover_names(notes, excerpts, pairs):
        for pair in person_card(name, pairs):
            if pair.pair_id in held:
                lines.append(f"- About {name}: {pair.prompt.strip()}")
    return CONTACT_HEADER + "\n" + "\n".join(lines) if lines else ""


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False, order: bool = False, figure: bool = False) -> str:
    picks = recent_picks(notes, excerpts, phrase, pairs, labels, holder, next_step, agreement, status, order, figure)
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
        if CONTACT_RE.search(req.user_input):
            named = await self.named_in_reading(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
            handed = handover_names(notes, found.excerpts, pairs) if guide_records.read(req.user_input).asks_holder else []
            notes = self.with_cards(notes, pairs, list(dict.fromkeys((named or []) + handed)) or None)
        guide = guide_records.read(req.user_input)
        # The lesson is in the outcome note, not in the latest passages, so a lesson question gets no latest-passages draft.
        # A work-address question wants the email, not the name: it gets the contact picks, not the holder draft.
        # A figure question combines the first figure with every later change, so the latest passages alone cannot settle it: no latest-passages draft.
        draft = "" if guide.asks_lesson or guide.asks_contact or guide.asks_figure or guide_records.asks_order(req.user_input) else await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft)
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        guide = guide_records.read(req.user_input)
        picks = recent_picks(notes, excerpts, phrase, pairs, holder=guide.asks_holder, next_step=guide.asks_next_step, agreement=guide.asks_disagreement, status=guide.asks_status)
        if not picks:
            return ""
        system = " ".join([LATEST_SYSTEM, DISAGREE_DRAFT_SYSTEM] if guide.asks_disagreement else [LATEST_SYSTEM, HOLDER_DRAFT_SYSTEM] if guide.asks_holder else [LATEST_SYSTEM, *guide_records.latest_notes(req.user_input)])
        messages = [{"role": "system", "content": short_system(req.system_prompt, system)}, {"role": "user", "content": LATEST_BRIEF.format(passages="\n".join(passage for _, passage in picks), message=req.user_input)}]
        reply = await consult(self.engine.llm, self.engine.tally, req, messages, self.max_tokens, self.effort, deadline, outcome, "latest passages reading")
        written = drafted(reply)
        outcome.events.append(f"latest passages reading: {'draft' if written else 'no draft'}")
        return (reply or "").strip() if written else ""

    async def named_in_reading(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> list[str] | None:
        reply = await consult(self.engine.llm, self.engine.tally, req, topic_messages(req, notes, excerpts, phrase, pairs) + [{"role": "user", "content": PERSON_BRIEF}], self.max_tokens, self.effort, deadline, outcome, "thread reading")
        named = full_names(SPACE.sub(" ", reply or ""), pairs)
        outcome.events.append(f"thread reading named {len(named)}")
        return named or None


def topic_messages(req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], draft: str = "") -> list[dict[str, Any]]:
    guide = guide_records.read(req.user_input)
    recent = recent_view(notes, excerpts, phrase, pairs, holder=guide.asks_holder, next_step=guide.asks_next_step, agreement=guide.asks_disagreement, status=guide.asks_status, order=guide_records.asks_order(req.user_input), figure=guide.asks_figure)
    beside = f"\n\n{recent}" if recent else ""
    after = f"\n\n{DRAFT_NOTE.format(draft=draft)}" if draft else ""
    contact = f"\n\n{contact_view(notes, excerpts, pairs)}" if guide.asks_contact else ""
    # A disagreement question often ends with "all of them" or "each record"; the draft note stands after the message so the form it names is the last thing read.
    tail = after if guide.asks_disagreement else ""
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{beside}{contact}{'' if tail else after}\n\n{MESSAGE_HEADER}\n{req.user_input}{tail}"
    return [{"role": "system", "content": short_system(req.system_prompt, topic_system(req.user_input))}, {"role": "user", "content": user}]


def topic_system(message: str) -> str:
    system = TOPIC_SYSTEM.replace(VALUE_VERBATIM, guide_records.words_rule(VALUE_VERBATIM, message), 1)
    return " ".join([guide_records.topic_answer_line(system, message), *guide_records.notes(message)])


@dataclass(frozen=True)
class TopicNotes:
    topic: Topic
    notes: list[MemoryPair]
    excerpts: dict[str, str]


PERSON_DETAIL_RE = re.compile(r"\b(?:e-?mail|work address|handle|signal|whatsapp|telegram|phone number|contact)\b", re.IGNORECASE)
NAMED_PERSON_RE = re.compile(r"(?<![.!?:]\s)(?<!^)\b[A-Z][a-z]+ [A-Z][a-z]+\b")


def find_topic(question: str, pairs: list[MemoryPair], min_density: int, max_chars: int) -> TopicNotes | None:
    if not pairs or QUOTE_RE.search(question) or full_names(question, pairs):
        return None
    # A question for a named person's email, address or handle is about that person, not about the event it mentions in passing ("the
    # year-end summer camp"): it stays off the topic path even where the person is not on record.
    if PERSON_DETAIL_RE.search(question) and NAMED_PERSON_RE.search(question):
        return None
    index = TopicIndex(pairs)
    topic = index.topic(question)
    if topic is None or topic.densest < min_density:
        return None
    excerpts = index.excerpt(topic)
    whole = {pair.pair_id: pair for pair in pairs}
    # A story note names its thread in several paragraphs, but the notes' misspellings can leave only one of them readable as the phrase:
    # a note whose own text runs to many paragraphs is a story note of the thread wherever the phrase is found in it.
    dense = [pair for pair in excerpts if PARAGRAPH_BREAK in pair.prompt or whole[pair.pair_id].prompt.count(PARAGRAPH_BREAK) >= STORY_NOTE_PARAGRAPHS]
    if len(dense) < MIN_DENSE_NOTES:
        return None
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
    recent = recent_view(found.notes, found.excerpts, phrase, pairs, labels)
    return whole, passages_view(found.notes, found.excerpts, phrase, labels) + (f"\n\n{recent}" if recent else "")


def nicknames(pairs: list[MemoryPair]) -> set[str]:
    return {alias for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS for alias in ALIAS_RE.findall(pair.prompt)}


def thread_of(question: str, notes: list[MemoryPair], pairs: list[MemoryPair]) -> list[MemoryPair]:
    patterns = [re.compile(r"\b" + re.escape(nick) + r"\b") for nick in sorted(nicknames(pairs)) if re.search(r"\b" + re.escape(nick) + r"\b", question)]
    if not patterns:
        return notes
    thread = [pair for pair in notes if any(pattern.search(pair.prompt) for pattern in patterns)]
    if sum(1 for pair in thread if PARAGRAPH_BREAK in pair.prompt) < MIN_THREAD_NOTES:
        return notes
    return thread
