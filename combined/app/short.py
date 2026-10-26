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

from .action import OPERATOR_SEAM, VALUE_VERBATIM, Outcome, TokenTally
from .answer import parse_slot
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, asked_part, identifier_tokens, tokens
from .memory.people import ALIAS_RE, SHORT_RECORD_CHARS, by_date, cards_for, full_names
from .memory.topic import Topic, TopicIndex, paragraphs, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_ANSWER_LINE = "Reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
PROGRAM_SYSTEM = f"{SHORT_OPENING} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year, even when the message asks for less. If the notes do not state it, say so."
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year. If the notes do not state it, say so."
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MARK_RE = re.compile(r"\bM(\d+)\b")
ORDER_SYSTEM = "You read a user's saved notes and put them in the order the things they describe must have happened. Do not answer anything else."
ORDER_BRIEF = "{notes}\n\nThe notes above are listed in no particular order. Judging from their words, put them in the order the things they describe happened: a note that refers back to an earlier state of the same thing comes after the note that set that state. Reply with one line: the marks in that order, separated by commas."
MIN_SECONDS = 8.0
READINGS_HELD = 512
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
LEAD_HEADER = "The statements of the notes below, in the order an earlier reading of their words put them:"
LEAD_MAX_STATEMENT_CHARS = 1000
PROGRAM_MAX_RECORD_CHARS = 2000
PERSON_BRIEF = "Before the message is answered: which person is it asking about? Reply with that person's full name as the notes give it, and nothing else."
RECENT_HEADER = "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:"
RECENT_LINE = "- The most recent passage about “{phrase}”: {passage}"
RECENT_PERSON_LINE = "- The most recent passage about “{phrase}” that names a person: {passage}"
RECUR_SHARE = 0.8
RECUR_EXTRA_WORDS = 6
RECUR_TIMES = 2
RECUR_MAX_WORDS = 40
RECUR_TYPO_WORD = 4
LATEST_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
LATEST_BRIEF = "Passages:\n{passages}\n\nMessage:\n{message}"
SHARED_DRAFT_NOTE = "A draft reply, written once from these same notes for the question \"{asked}\"; it has not been checked, and the notes decide wherever they differ:\n{draft}\n\nCheck the draft against the notes, then reply to the message as asked at the start."
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


def by_statement(records: list[MemoryPair], token: str) -> list[list[MemoryPair]]:
    groups: dict[str, list[MemoryPair]] = {}
    for pair in sorted(records, key=lambda p: (p.timestamp, p.pair_id)):
        groups.setdefault(statement(pair, token), []).append(pair)
    return list(groups.values())


def by_text(groups: list[list[MemoryPair]], token: str) -> list[list[MemoryPair]]:
    return sorted(groups, key=lambda group: statement(group[0], token).lower())


def listing(groups: list[list[MemoryPair]], token: str) -> str:
    return "\n\n".join(f"[M{mark}]\nUser: {statement(group[0], token)}" for mark, group in enumerate(groups, start=1))


def sequence_from(reply: str, groups: list[list[MemoryPair]]) -> list[list[MemoryPair]]:
    marks = [int(mark) for mark in MARK_RE.findall(reply)]
    chosen = [groups[mark - 1] for mark in dict.fromkeys(marks) if 1 <= mark <= len(groups)]
    return chosen + [group for group in groups if group not in chosen]


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


def lead_view(groups: list[list[MemoryPair]], token: str) -> str:
    statements = [statement(group[0], token) for group in groups]
    if len(statements) < 2 or any(len(text) > LEAD_MAX_STATEMENT_CHARS for text in statements):
        return ""
    return LEAD_HEADER + "\n" + "\n".join(f"{mark}. {text}" for mark, text in enumerate(statements, start=1))


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome) -> bool:
    if deadline - time.monotonic() < MIN_SECONDS:
        outcome.events.append("deciding call: no time left")
        return False
    await engine.converse(req, messages, None, effort, max_tokens, deadline, outcome, checkable=True)
    return bool(outcome.content.strip())


def program_messages(system: str, shown: str, note: str, message: str) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": f"{shown}\n\n{note}{MESSAGE_HEADER}\n{message}"}]


class ShortPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, readings: dict[str, asyncio.Future[str | None]], order_max_tokens: int, drafts: dict[str, asyncio.Future[str | None]]) -> None:
        self.engine = engine
        self.llm = engine.llm
        self.tally = engine.tally
        self.readings = readings
        self.drafts = drafts
        self.effort = effort
        self.max_tokens = max_tokens
        self.order_max_tokens = order_max_tokens

    async def call(self, req: RunRequest, messages: list[dict[str, Any]], max_tokens: int, deadline: float, outcome: Outcome, what: str) -> str | None:
        return await consult(self.llm, self.tally, req, messages, max_tokens, self.effort, deadline, outcome, what)

    async def read_order(self, req: RunRequest, messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> str | None:
        readings = self.readings
        key = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
        held = readings.get(key)
        if held is not None:
            outcome.events.append("order pass: the same notes were already read in this run")
            return await asyncio.shield(held)
        held = asyncio.get_running_loop().create_future()
        readings[key] = held
        while len(readings) > READINGS_HELD:
            del readings[next(iter(readings))]
        reply: str | None = None
        try:
            reply = await self.call(req, messages, self.order_max_tokens, deadline, outcome, "order pass")
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
        groups = await self.groups(req, records, token, deadline, outcome)
        if groups is None:
            return False
        notes = grouped_view(groups)
        lead = lead_view(groups, token)
        opening = f"{lead}\n\n" if lead else ""
        system = short_system(req.system_prompt, PROGRAM_SYSTEM)
        shown = f"{opening}{NOTES_HEADER}\n\n{notes}"
        asked = asked_part(req.user_input)
        key = hashlib.sha256(json.dumps([normalize_user_id(req.user_id), system, shown, asked]).encode()).hexdigest()
        draft = await self.shared_draft(req, key, program_messages(system, shown, "", req.user_input), deadline, outcome)
        note = SHARED_DRAFT_NOTE.format(asked=asked, draft=draft.strip()) + "\n\n" if draft is not None else ""
        outcome.events.append(f"short path records={len(records)} groups={len(groups)}{' shared draft' if note else ''}")
        return await decide(self.engine, req, program_messages(system, shown, note, req.user_input), self.effort, self.max_tokens, deadline, outcome)

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


def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None) -> list[tuple[str, str]]:
    passages = dated_passages(notes, excerpts, labels)
    if not passages:
        return []
    others = other_paragraphs(notes, pairs)
    misspelt: dict[tuple[str, str], bool] = {}
    kept = [passage for passage in passages if not recurs(passage_shape(passage[1], phrase), others, misspelt)] or passages
    last = kept[-1]
    picks = [(RECENT_LINE, f"{last[0]} {last[1]}")]
    named = next((passage for passage in reversed(kept) if full_names(passage[1], pairs)), None)
    if named is not None and named is not last:
        picks.append((RECENT_PERSON_LINE, f"{named[0]} {named[1]}"))
    return picks


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None) -> str:
    picks = recent_picks(notes, excerpts, phrase, pairs, labels)
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
            notes = self.with_cards(notes, pairs, await self.named_in_reading(req, notes, found.excerpts, phrase, pairs, deadline, outcome))
        draft = await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft)
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        picks = recent_picks(notes, excerpts, phrase, pairs)
        if not picks:
            return ""
        messages = [{"role": "system", "content": short_system(req.system_prompt, LATEST_SYSTEM)}, {"role": "user", "content": LATEST_BRIEF.format(passages="\n".join(passage for _, passage in picks), message=req.user_input)}]
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
    recent = recent_view(notes, excerpts, phrase, pairs)
    beside = f"\n\n{recent}" if recent else ""
    after = f"\n\n{DRAFT_NOTE.format(draft=draft)}" if draft else ""
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{beside}{after}\n\n{MESSAGE_HEADER}\n{req.user_input}"
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
