from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from .action import OPERATOR_SEAM, VALUE_VERBATIM, Outcome, TokenTally
from . import guide_records
from .answer import parse_slot
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, asked_part, identifier_tokens, tokens
from .memory.people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS, by_date, cards_for, full_names
from .memory.topic import Topic, TopicIndex, paragraphs, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_ANSWER_LINE = "Reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
CASE_FILE_OPENING = "You are Ditto, the user's assistant with long-term memory. The saved notes below are the entries of one case file, and the message is answered from them alone."
# How a reply to a case-file question is worded: the value that holds now and nothing that could be read as another
# candidate for it.
ANSWER_RULES = ("A reply states the value that holds now and only that value: it names no earlier value, no other candidate "
                "and no other item, says nothing about how the value came to be, and does not hedge, ask back or correct "
                "itself. An action is given without when it is due. A time is written on the 24-hour clock, such as 17:55.")
PROGRAM_SYSTEM = f"{CASE_FILE_OPENING} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Every date you give is written in full, day, month and year, however briefly the message asks. {ANSWER_RULES}"
# How a case file's entries are read into a ledger. Each rule is a general reading of records (their order, labels,
# and what a later entry does to an earlier one); none of them names a field, a value or a question form.
READING_RULES = (
    "Order: the entries are listed by the time they were filed, earliest first, and that is the order things happened in. "
    "A number inside an entry (a note, row, line or entry number) is not its place in that order. Where an entry itself "
    "dates an event, that date places the event.",
    "Labels: where an entry defines what a label, code or field name means, every use of it is read by that meaning, and a "
    "thing described by its purpose is the one whose entries carry that description, however it is spelled.",
    "Separate matters: an entry that says it concerns a separate or unrelated matter changes nothing about the others.",
    "Changes: a value set or changed holds until a later entry changes it. A change only proposed or suggested holds once "
    "an entry says it went ahead; one declined, turned down, withdrawn or dropped changes nothing. An entry saying an "
    "earlier one was wrong, a mistake, struck or to be disregarded cancels that earlier change, and the value before it "
    "holds again; an entry saying an earlier one was checked and stands changes nothing.",
    "Going back: an entry that goes back to the previous entry or arrangement is itself the latest change, and it undoes "
    "the change before it, so the value before that change holds again: after A, then B, then C, going back gives B. "
    "Going back to the original gives the first value; going back to a named value gives that value.",
    "Lists: a list starts from its first full form, and every addition, removal, swap and return applies in turn; what "
    "holds is the whole list after the last entry.",
    "Plans: a step marked done or dropped is closed until an entry reopens it; the step that holds is the earliest open "
    "one in the plan's order, with the owner the latest entry gives it.",
    "Roles: whoever something was last handed to holds it, and whoever performed a step is its actor; the party that "
    "commissions the work and pays is the client, and the party paid for supplying it is the vendor.",
    "Dates: what held as of a date is the latest change dated on or before it, and events are put in order by their dates, "
    "worked out where an entry dates one relative to another.",
    "People: a person named another way (initials, a role, a nickname) is the one the entries say it stands for, and a "
    "contact is the handle or address the entries list for that person, exactly as written there.",
    "Values: each value is written with all of its own words exactly as the entry gives it, and nothing more: no timing, "
    "reason or sentence around it.",
)
LEDGER_SYSTEM = "You keep the ledger of one case file in the user's saved notes. You read its entries and write down what each tracked thing is and how it changed. You answer nothing else."
LEDGER_BRIEF = (
    "{notes}\n\nWrite the ledger of this case file. First, for every label, code or field name an entry defines, one line "
    "'LABEL label: what it means'. Then go through the entries in filing order and, for every entry that sets or changes "
    "something tracked, one line '[mark] item: before -> after (what the entry did)'. For an event an entry dates, one "
    "line 'DATED item: value (date)'. Last, for each item, one line 'NOW item: value' with what holds after the last "
    "entry: a list whole, a plan's first open step with its owner."
)
LEDGER_MAX_TOKENS = 8000
LEDGER_ASK = "Before replying, write the ledger of these entries."
CLOSING_NOTE = ("Before replying, apply every entry in order. The message asks for what stands after the last entry, with every "
                "change applied: one value, or the whole list, not one value per change. Going back to the previous entry "
                "restores the value before the latest change still standing (A, then B, then C, then back: B); an entry "
                "struck as wrong leaves the value before it.")
# The ledger is the one reading of the entries. A reply told to re-read them goes back to the raw sentence and its
# default misreading, so the reply takes the value from the ledger and only words it.
REPLY_NOTE = ("Answer the message from the ledger, which already applies every entry: take what it holds for the thing the "
              "message asks about (its NOW line, or its DATED lines when the message asks about a date or an order of events), "
              "finding that thing through the labels the ledger lists. Reply in one plain sentence that gives that value and "
              "nothing else, then the line 'ANSWER: …'.")
REWORDED_NOTE = ("The same question, asked in other words:\n{message}\n\nReply to it as it is asked, with the same value in the "
                 "same words as the reply above: one plain sentence, then the line 'ANSWER: …'.")
COPY_RATIO = 0.75
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year. If the notes do not state it, say so."
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MIN_SECONDS = 8.0
SHARED_HELD = 512
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
FILED_LEAD_HEADER = "The statements of the notes below, oldest first, each after the day its note was filed:"
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


def filed_lead(notes: list[MemoryPair], token: str) -> str:
    statements = [statement(pair, token) for pair in notes]
    if len(statements) < 2 or any(len(text) > LEAD_MAX_STATEMENT_CHARS for text in statements):
        return ""
    return FILED_LEAD_HEADER + "\n" + "\n".join(f"{mark}. {pair.timestamp[:10]}: {text}" if pair.timestamp else f"{mark}. {text}" for mark, (pair, text) in enumerate(zip(notes, statements), start=1))


def alike(first: str, second: str) -> bool:
    matcher = SequenceMatcher(None, first, second, autojunk=False)
    return matcher.quick_ratio() >= COPY_RATIO and matcher.ratio() >= COPY_RATIO


def once_each(notes: list[MemoryPair], token: str) -> list[MemoryPair]:
    """Notes in the order given, with copies of one statement filed in the same minute shown once.

    A copy is a note of the same minute whose statement reads like the first one's within COPY_RATIO, which a
    retyped or reformatted copy does and a different statement does not. Of a set of copies the one shown is the
    one closest to the others, then the earliest id; a note without a filing time is never a copy."""
    sets: list[list[tuple[MemoryPair, str]]] = []
    for pair in notes:
        said = statement(pair, token).lower()
        home = next((group for group in sets if pair.timestamp and group[0][0].timestamp[:16] == pair.timestamp[:16] and alike(group[0][1], said)), None)
        if home is None:
            sets.append([(pair, said)])
        else:
            home.append((pair, said))
    return [closest(group) for group in sets]


def closest(group: list[tuple[MemoryPair, str]]) -> MemoryPair:
    if len(group) == 1:
        return group[0][0]
    nearness = [sum(SequenceMatcher(None, said, other, autojunk=False).ratio() for _, other in group) for _, said in group]
    best = min(range(len(group)), key=lambda index: (-nearness[index], group[index][0].pair_id))
    return group[best][0]


def shared_key(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome, check_unanswered_only: bool = False) -> bool:
    if deadline - time.monotonic() < MIN_SECONDS:
        outcome.events.append("deciding call: no time left")
        return False
    start = len(messages)
    await engine.converse(req, messages, None, effort, max_tokens, deadline, outcome, checkable=True, check_unanswered_only=check_unanswered_only)
    if outcome.content.strip():
        return True
    engine.carried.extend(made_calls(messages[start:]))
    return False


def made_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("role") == "tool" or (message.get("role") == "assistant" and message.get("tool_calls"))]


def program_system(operator: str, message: str) -> str:
    return short_system(operator, " ".join([PROGRAM_SYSTEM, *guide_records.program_notes(message)]))


def ledger_messages(operator: str, notes: str) -> list[dict[str, Any]]:
    return [{"role": "system", "content": short_system(operator, " ".join([LEDGER_SYSTEM, *READING_RULES]))}, {"role": "user", "content": LEDGER_BRIEF.format(notes=notes)}]


def program_messages(system: str, shown: str, message: str, ledger: str | None = None, earlier: tuple[str, str] | None = None) -> list[dict[str, Any]]:
    """The deciding conversation. The ledger and an earlier rewording's reply go in as the assistant turns they were
    written as, after the request they answered; the first user turn always holds the notes and a message."""
    first = earlier[0] if earlier else message
    asked = f"{shown}\n\n{MESSAGE_HEADER}\n{first}"
    if ledger:
        turns = [{"role": "user", "content": f"{asked}\n\n{LEDGER_ASK}"}, {"role": "assistant", "content": ledger}, {"role": "user", "content": REPLY_NOTE}]
    else:
        turns = [{"role": "user", "content": f"{asked}\n\n{CLOSING_NOTE}"}]
    if earlier:
        turns += [{"role": "assistant", "content": earlier[1]}, {"role": "user", "content": REWORDED_NOTE.format(message=message)}]
    return [{"role": "system", "content": system}, *turns]


class ShortPath:
    """The program path: one case file's entries, read once into a ledger, then decided per message.

    Two things are shared between requests, both as model-written turns the deciding model reads and never as an
    answer the host gives: the ledger, written from the notes alone (no message), so every request over the same
    notes gets the same one; and the first decided reply to a question, which a later rewording of it over the same
    notes reads after its own question. The model writes every reply."""

    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, shared: dict[str, asyncio.Future[Any]]) -> None:
        self.engine = engine
        self.llm = engine.llm
        self.tally = engine.tally
        self.shared = shared
        self.effort = effort
        self.max_tokens = max_tokens

    async def call(self, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, deadline: float, outcome: Outcome, what: str) -> str | None:
        return await consult(self.llm, self.tally, req, messages, max_tokens, self.effort, deadline, outcome, what)

    async def answer(self, req: RunRequest, records: list[MemoryPair], token: str, deadline: float, outcome: Outcome) -> bool:
        notes = once_each(by_date(records), token)
        lead = filed_lead(notes, token)
        opening = f"{lead}\n\n" if lead else ""
        system = program_system(req.system_prompt, req.user_input)
        shown = f"{opening}{NOTES_HEADER}\n\n{record_view(notes)}"
        user = normalize_user_id(req.user_id)
        ledger = await self.ledger(req, notes, shared_key("ledger", user, req.system_prompt, shown), deadline, outcome)
        key = shared_key("reply", user, system, shown, asked_part(req.user_input))
        held = self.shared.get(key)
        outcome.events.append(f"short path records={len(records)} shown={len(notes)}{' ledger' if ledger else ''}")
        if held is not None:
            earlier = await self.wait_for(held, deadline, outcome, "earlier reply")
            return await decide(self.engine, req, program_messages(system, shown, req.user_input, ledger, earlier), self.effort, self.max_tokens, deadline, outcome, check_unanswered_only=True)
        mine = self.hold(key)
        decided = False
        try:
            decided = await decide(self.engine, req, program_messages(system, shown, req.user_input, ledger), self.effort, self.max_tokens, deadline, outcome, check_unanswered_only=True)
        finally:
            self.release(key, mine, (req.user_input, outcome.content) if decided and drafted(outcome.content) else None)
        return decided

    async def ledger(self, req: RunRequest, notes: list[MemoryPair], key: str, deadline: float, outcome: Outcome) -> str | None:
        if len(notes) < 2:
            return None
        held = self.shared.get(key)
        if held is not None:
            return await self.wait_for(held, deadline, outcome, "ledger")
        mine = self.hold(key)
        written: str | None = None
        try:
            messages = ledger_messages(req.system_prompt, record_view(notes))
            written = ((await self.call(req, messages, LEDGER_MAX_TOKENS, deadline, outcome, "ledger")) or "").strip() or None
        finally:
            self.release(key, mine, written)
        outcome.events.append(f"ledger: written here, {len(written.splitlines())} lines" if written else "ledger: none written")
        return written

    def hold(self, key: str) -> asyncio.Future[Any]:
        held: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self.shared[key] = held
        while len(self.shared) > SHARED_HELD:
            del self.shared[next(iter(self.shared))]
        return held

    def release(self, key: str, held: asyncio.Future[Any], text: Any) -> None:
        if text is None and self.shared.get(key) is held:
            del self.shared[key]
        if not held.done():
            held.set_result(text)

    async def wait_for(self, held: asyncio.Future[Any], deadline: float, outcome: Outcome, what: str) -> Any:
        try:
            text = await asyncio.wait_for(asyncio.shield(held), max(0.01, deadline - time.monotonic() - SHARED_WAIT_RESERVE))
        except TimeoutError:
            outcome.events.append(f"{what}: the one for the same notes is not ready in time")
            return None
        outcome.events.append(f"{what}: from an earlier request over the same notes" if text else f"{what}: none")
        return text


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


def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False) -> list[tuple[str, str]]:
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
        acting = next((passage for passage in reversed(passages) if ACTION_CUE_RE.search(passage[1]) and FULL_NAME_RE.search(passage[1])), None)
        if acting is not None:
            picks.append((RECENT_ACTION_LINE, f"{acting[0]} {acting[1]}"))
            return picks
    if status:
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
    return next((passage for passage in reversed(dated_passages(notes, excerpts, labels)) if HANDOVER_RE.search(passage[1]) and FULL_NAME_RE.search(passage[1])), None)


def handover_names(notes: list[MemoryPair], excerpts: dict[str, str], pairs: list[MemoryPair]) -> list[str]:
    handed = latest_handover(notes, excerpts)
    return full_names(handed[1], pairs) if handed is not None else []


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False) -> str:
    picks = recent_picks(notes, excerpts, phrase, pairs, labels, holder, next_step, agreement, status)
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
        draft = "" if guide.asks_holder or guide.asks_disagreement else await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft)
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        picks = recent_picks(notes, excerpts, phrase, pairs, status=guide_records.read(req.user_input).asks_status)
        if not picks:
            return ""
        messages = [{"role": "system", "content": short_system(req.system_prompt, " ".join([LATEST_SYSTEM, *guide_records.latest_notes(req.user_input)]))}, {"role": "user", "content": LATEST_BRIEF.format(passages="\n".join(passage for _, passage in picks), message=req.user_input)}]
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
    recent = recent_view(notes, excerpts, phrase, pairs, holder=guide.asks_holder, next_step=guide.asks_next_step, agreement=guide.asks_disagreement, status=guide.asks_status)
    beside = f"\n\n{recent}" if recent else ""
    after = f"\n\n{DRAFT_NOTE.format(draft=draft)}" if draft else ""
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{beside}{after}\n\n{MESSAGE_HEADER}\n{req.user_input}"
    return [{"role": "system", "content": short_system(req.system_prompt, topic_system(req.user_input))}, {"role": "user", "content": user}]


def topic_system(message: str) -> str:
    system = TOPIC_SYSTEM.replace(VALUE_VERBATIM, guide_records.words_rule(VALUE_VERBATIM, message), 1)
    return " ".join([guide_records.topic_answer_line(system, message), *guide_records.notes(message)])


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
