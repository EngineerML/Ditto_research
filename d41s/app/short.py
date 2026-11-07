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
from . import guide_records
from .answer import parse_slot
from .llm import LLM, LLMError
from .memory.retrieval import QUOTE_RE, Candidate, asked_part, identifier_tokens, tokens
from .memory.people import ALIAS_RE, FULL_NAME_RE, SHORT_RECORD_CHARS, by_date, cards_for, full_names, person_card
from .memory.topic import Topic, TopicIndex, paragraphs, typo_of
from .packet import Packet
from .protocol import MemoryPair, RunRequest, normalize_user_id
from .records import RecordsEngine

log = logging.getLogger("harness.short")

SHORT_OPENING = "You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes below."
NOTES_TOGETHER = "Read every note before answering. When several notes speak of the same person, thread or reference, read them together, with their dates, before deciding what holds now."
SHORT_ANSWER_LINE = "Reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the notes put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
PROGRAM_SYSTEM = f"{SHORT_OPENING} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year, even when the message asks for less. If the notes do not state it, say so."
TOPIC_SYSTEM = f"{SHORT_OPENING} {NOTES_TOGETHER} {VALUE_VERBATIM} {SHORT_ANSWER_LINE} Write any date in full, with day, month and year. {guide_records.TOPIC_NO_RECORD}"
NOTES_HEADER = "Saved notes:"
MESSAGE_HEADER = "Message:"
EDGE = " \t\r\n:;.,-–—|\"'“”‘’`"
SPACE = re.compile(r"\s+")
MIN_SECONDS = 8.0
DRAFTS_HELD = 512
CONTACT_RE = re.compile(r"\b(?:e-?mail|address)\b", re.IGNORECASE)
MIN_DENSE_NOTES = 3
MIN_THREAD_NOTES = 2
PARAGRAPH_BREAK = "\n\n"
PASSAGES_HEADER = "Passages that name “{phrase}”, copied from the notes below:"
FILED_LEAD_HEADER = "The statements of the notes below, oldest first, each after the day its note was filed; a statement that several notes repeat word for word is listed once:"
UNDONE_MARK = " (this note names no value: it undoes the latest change before it, so the value before that change holds again)"
CHAIN_NOTE = "The notes are listed oldest first by the day each was filed, the order they were written in. Read them in that order as one sequence before answering. A later note can change a value or bring an earlier one back. A note saying that an earlier entry was a mistake, wrong or struck undoes that entry entirely, together with anything it said about the entries before it, so what held before that entry holds again; a suggested change holds only once a note says it went ahead, and one turned down changes nothing. What holds now is what the whole sequence leaves in place. Where a note itself says on what day something happened or took effect, that day, not its filing day, places it in time. Give the value that holds now once, on its own: not the earlier values, not the steps that led to it, and not the sentence of the note that set it."
LEAD_MAX_STATEMENT_CHARS = 1000
PROGRAM_MAX_RECORD_CHARS = 2000
PERSON_BRIEF = "Before the message is answered: which person is it asking about? Reply with that person's full name as the notes give it, and nothing else."
RECENT_HEADER = "Picked out by code from the dates of the notes and the order of the passages within each note, leaving out passages that recur almost word for word in the notes about other things; not checked — the notes above decide wherever they differ:"
RECENT_LINE = "- The most recent passage about “{phrase}”: {passage}"
RECENT_HANDOVER_LINE = "- The most recent passage about “{phrase}” that puts a person in charge of it: {passage}"
HANDOVER_RE = re.compile(r"\b(?:handed (?:over )?to|handed \w+ (?:\w+ )?to|passed [^.;]{0,40}\bto\b|picked up [^.;]{0,40}\bfrom\b|is the owner|owner now|now owns|ownership of|'s now|in charge|to run\b|holding the thread|the handoff|run point|took it on|the one accountable|owning|a name on it)", re.IGNORECASE)
RECENT_LATER_STEP_LINE = "- A later passage about “{phrase}” that gives a person the next step or the ball, which does not by itself hand the work to them: {passage}"
RECENT_ACTION_LINE = "- The most recent passage about “{phrase}” that gives a next action to a person: {passage}"
ACTION_CUE_RE = re.compile(r"\b(?:next step|next move|next from them|first action from|follow-up for|open action|is waiting on|the ball is with|agreed to|is going to|will \w+|would \w+|next on)\b", re.IGNORECASE)
RECENT_PERSON_LINE = "- The most recent passage about “{phrase}” that names a person: {passage}"
RECENT_EMAIL_LINE = "- The most recent note that gives a work email for {person}{called}: {passage}"
CALLED = ", whom the notes also call “{alias}”"
EMAIL_ADDRESS_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CUE_WORDS = ("handed", "handoff", "passed", "picked", "ownership", "owner", "owns", "owning", "charge", "holding", "thread", "accountable", "point", "took", "next", "step", "move", "first", "action", "from", "follow", "open", "waiting", "ball", "agreed", "going")
WORD_RE = re.compile(r"[A-Za-z]+")
RECENT_NOTE_LINE = "- The last passage about “{phrase}” in one of the two latest notes about it: {passage}"
RECUR_SHARE = 0.8
RECUR_EXTRA_WORDS = 6
RECUR_TIMES = 2
RECUR_MAX_WORDS = 40
RECUR_TYPO_WORD = 4
LATEST_SYSTEM = "You are Ditto, the user's assistant with long-term memory. Below are the latest passages of a longer thread in the user's saved notes. Answer the message only if these passages settle it by themselves. If the answer depends on anything earlier in the thread, reply with one sentence saying that these passages do not settle it, and nothing else. Otherwise reply briefly, then end with one final line 'ANSWER: <only the value asked for, as short as the passages put it, in their words>'; when several things are asked, give them on that line in the order asked, separated by ' ; '."
LATEST_BRIEF = "Passages:\n{passages}\n\nMessage:\n{message}"
SHARED_DRAFT_NOTE = "A reply written once from these same notes for this same question, worded \"{asked}\":\n{draft}\n\nReplies to one question must agree however it is worded: give the same value as that reply, even where you would read the notes another way, in the form this message asks for."
SHARED_RULE = "An earlier reply to the same question, when one is shown before the message, gives the value: replies to one question must agree however it is worded, so give the same value as that reply, even where you would read the notes another way, in the form the message asks for."
SHARED_WAIT_RESERVE = 60.0
DRAFT_WAITS = 2
HOLDING_NOTE = "\"After every recorded handover\" here means once all of them are applied, not after each one: the message asks for one person, whoever has it now, the last person it was handed or passed to. Someone who only did a step on it, or had it before, is not the answer. Give that one name."
HOLDER_PERSON_NOTE = "\"After every recorded reassignment\" here means once all of them are applied, not after each one: the message asks for one person, whoever holds the role now, the one the latest reassignment puts in it. Where the notes name that person by a contact, the person is the one the notes list for that contact. Give that one name, not anyone who held the role before."
HOLDER_CONTACT_NOTE = "\"After every recorded reassignment\" here means once all of them are applied, not after each one: the message asks how to reach one person, whoever holds the role now, the one the latest reassignment puts in it, perhaps by initial and surname. The answer is the contact the notes list for that person, exactly as listed: the contact itself, not their name, and no one else's contact."
ONE_HOLDER_LINE = "this message asks for one person or one contact, so that line holds exactly one, written out on that line itself, with no second name or contact on any line after it."
QUESTION_WORD_RE = re.compile(r"[a-z]+")
EVERY_WORDS = ("every", "each")
CHANGE_WORDS = ("reassignment", "handover")
HOLDER_FORMS = ((("who", "is", "holding"), HOLDING_NOTE), (("which", "person"), HOLDER_PERSON_NOTE), (("contact",), HOLDER_CONTACT_NOTE))
DRAFT_NOTE = "A draft reply, written from a reading of only the passages picked out above:\n\n{draft}\n\nCheck the draft against every note above, then reply to the message as asked at the start: briefly, ending with the line 'ANSWER: …', without mentioning the draft."
READING_HEADER = "Picked by code from the wording of the message and of the notes, as a guide to reading them; the notes decide:"
AFTER_CHANGE_NOTE = "Where the message asks about something after a change, a handover or the like, without asking what came next, it asks what holds now, once every note is applied: not what held right after that one change, so a later note still counts."
PLAN_NOTE = "The message asks what the plan for it is now: the action the notes last settled on and did not take back. A change that was only proposed or requested, and then dropped or turned down, leaves the plan as it was before it; a note that takes the plan back to an earlier arrangement brings back the action that held then. Give that action alone, in the words the notes use for the action itself, and end the answer line where the action ends: leave out any words about when it is due, such as before then, before it renews or a date, and give no sentence about a note."
BROUGHT_BACK_NOTE = "A note that sends something back to the previous entry or arrangement, or to what it was before the last change, undoes the latest change before that note: pass over the value that change set and take the value that held before it. A note that sends it back to the original entry or the first arrangement brings back the first value. Such a note names no value of its own: give the value it brings back, never the value of the change it undoes."
STRUCK_VALUE_NOTE = "A note that strikes an earlier entry, or says a change did not go ahead, names the value of that entry or change, perhaps written another way than the entry wrote it, such as a time as 1:25 pm where the entry says 13:25: it is still that entry or that change."
TIMES_HEADER = "Times written in the notes, each in 24-hour form with the ways the notes write it:"
AFTER_CHANGE_RE = re.compile(r"\bafter the \w", re.IGNORECASE)
SEQUENCE_WORD_RE = re.compile(r"\b(?:next|came|comes|immediately|right|just|before|first|earlier|order|middle|point|ignoring)\b", re.IGNORECASE)
PLAN_WORD_RE = re.compile(r"\b(?:doing|decid\w*|decision|settled?|plans?|action)\b", re.IGNORECASE)
WHAT_RE = re.compile(r"\bwhat\b", re.IGNORECASE)
BROUGHT_BACK_RE = re.compile(r"\b(?:previous (?:entry|arrangement)|original entry|before the (?:last|most recent) change|went back to|is back to|goes back to|returned to|reverts? to)\b", re.IGNORECASE)
STRUCK_RE = re.compile(r"\b(?:mistake|wrong|struck|in error|did not go ahead|turned down|dropped|declined|withdrawn)\b", re.IGNORECASE)
UNDO_RE = re.compile(r"\b(?:reverts?|went back|goes back|is back|was back|returned) to\b.*\b(?:previous|earlier|prior|before)\b", re.IGNORECASE)
CLOCK_RE = re.compile(r"(?<![\w:.])(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?\s?m\b|(?<![\w:.])(\d{1,2}):(\d{2})(?![\w:]|\.\d)", re.IGNORECASE)


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
    return FILED_LEAD_HEADER + "\n" + "\n".join(lead_line(mark, pair, text) for mark, (pair, text) in enumerate(once_a_day(notes, statements), start=1))


def once_a_day(notes: list[MemoryPair], statements: list[str]) -> list[tuple[MemoryPair, str]]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    kept: list[tuple[MemoryPair, str]] = []
    for pair, text in zip(notes, statements):
        said = (pair.timestamp[:10], tuple(tokens(text)))
        if said not in seen:
            seen.add(said)
            kept.append((pair, text))
    return kept


def lead_line(mark: int, pair: MemoryPair, text: str) -> str:
    shown = text + UNDONE_MARK if UNDO_RE.search(text) else text
    return f"{mark}. {pair.timestamp[:10]}: {shown}" if pair.timestamp else f"{mark}. {shown}"


async def decide(engine: RecordsEngine, req: RunRequest, messages: list[dict[str, Any]], effort: str, max_tokens: int, deadline: float, outcome: Outcome, checkable: bool = False) -> bool:
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


def spelled_at(words: list[str], start: int, form: tuple[str, ...]) -> bool:
    return start + len(form) <= len(words) and all(typo_of(target, words[start + k]) for k, target in enumerate(form))


def after_every_change(words: list[str]) -> bool:
    for at in range(len(words) - 2):
        if typo_of("after", words[at]) and any(typo_of(every, words[at + 1]) for every in EVERY_WORDS) and any(typo_of(change, word) for word in words[at + 2:at + 5] for change in CHANGE_WORDS):
            return True
    return False


def holder_note(message: str) -> str:
    words = QUESTION_WORD_RE.findall(message.lower())
    if not after_every_change(words):
        return ""
    return next((note for form, note in HOLDER_FORMS if any(spelled_at(words, at, form) for at in range(len(words)))), "")


def asks_after_change(message: str) -> bool:
    asked = asked_part(message)
    return bool(AFTER_CHANGE_RE.search(asked)) and not SEQUENCE_WORD_RE.search(asked)


def asks_plan(message: str) -> bool:
    asked = asked_part(message)
    return bool(PLAN_WORD_RE.search(asked)) and bool(WHAT_RE.search(asked))


def reading_notes(message: str, notes: list[MemoryPair]) -> list[str]:
    written = "\n".join(pair.prompt for pair in notes)
    struck = bool(STRUCK_RE.search(written)) and bool(times_view(notes))
    return [note for note, routed in ((AFTER_CHANGE_NOTE, asks_after_change(message)), (PLAN_NOTE, asks_plan(message)), (BROUGHT_BACK_NOTE, bool(BROUGHT_BACK_RE.search(written))), (STRUCK_VALUE_NOTE, struck)) if routed]


def clock(match: re.Match[str]) -> str:
    if match.group(3):
        hour, minute = int(match.group(1)) % 12 + (12 if match.group(3).lower() == "p" else 0), int(match.group(2) or 0)
    else:
        hour, minute = int(match.group(4)), int(match.group(5))
    return f"{hour:02d}:{minute:02d}" if hour < 24 and minute < 60 else ""


def times_view(notes: list[MemoryPair]) -> str:
    forms: dict[str, list[str]] = {}
    for pair in notes:
        for match in CLOCK_RE.finditer(pair.prompt):
            value = clock(match)
            if value and match.group(0).strip() not in forms.setdefault(value, []):
                forms[value].append(match.group(0).strip())
    lines = [f"- {value}: {', '.join(written)}" for value, written in sorted(forms.items()) if written != [value]]
    return TIMES_HEADER + "\n" + "\n".join(lines) if lines else ""


def reading_view(reading: list[str], notes: list[MemoryPair]) -> str:
    if not reading:
        return ""
    times = times_view(notes) if STRUCK_VALUE_NOTE in reading else ""
    return READING_HEADER + "\n" + "\n".join(f"- {note}" for note in reading) + (f"\n\n{times}" if times else "") + "\n\n"


def program_system(operator: str, message: str, shared: bool, reading: list[str] | None = None) -> str:
    note = "" if shared else holder_note(message)
    own = " ".join([PROGRAM_SYSTEM, CHAIN_NOTE, *([SHARED_RULE] if shared else []), *guide_records.program_notes(message), *([note] if note else []), *([] if shared else reading or [])])
    return short_system(operator, own.replace(guide_records.SEVERAL_SEMI, ONE_HOLDER_LINE, 1) if note else own)


def program_messages(system: str, shown: str, note: str, message: str) -> list[dict[str, Any]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": f"{shown}\n\n{note}{MESSAGE_HEADER}\n{message}"}]


class ShortPath:
    def __init__(self, engine: RecordsEngine, *, effort: str, max_tokens: int, drafts: dict[str, asyncio.Future[str | None]]) -> None:
        self.engine = engine
        self.drafts = drafts
        self.effort = effort
        self.max_tokens = max_tokens

    async def answer(self, req: RunRequest, records: list[MemoryPair], token: str, deadline: float, outcome: Outcome) -> bool:
        notes = by_date(records)
        lead = filed_lead(notes, token)
        opening = f"{lead}\n\n" if lead else ""
        reading = reading_notes(req.user_input, notes)
        system = program_system(req.system_prompt, req.user_input, False, reading)
        shown = f"{opening}{NOTES_HEADER}\n\n{record_view(notes)}"
        guide = reading_view(reading, notes)
        asked = asked_part(req.user_input)
        key = hashlib.sha256(json.dumps([normalize_user_id(req.user_id), system, shown, asked]).encode()).hexdigest()
        note, held = await self.shared_draft(key, deadline, outcome)
        if held is not None:
            outcome.events.append(f"short path records={len(records)}{' reading notes' if guide else ''}")
            return await self.first_reply(req, key, held, program_messages(system, shown, guide, req.user_input), deadline, outcome)
        shared = note + "\n\n" if note is not None else ""
        outcome.events.append(f"short path records={len(records)}{' shared draft' if shared else ' reading notes' if guide else ''}")
        if shared:
            system = program_system(req.system_prompt, req.user_input, True)
        return await decide(self.engine, req, program_messages(system, shown, shared or guide, req.user_input), self.effort, self.max_tokens, deadline, outcome)

    async def shared_draft(self, key: str, deadline: float, outcome: Outcome) -> tuple[str | None, asyncio.Future[str | None] | None]:
        shared: str | None = None
        for _ in range(DRAFT_WAITS):
            held = self.drafts.get(key)
            if held is None:
                return None, self.hold(key)
            shared = await self.earlier_draft(held, deadline, outcome)
            if shared is not None or self.drafts.get(key) is held:
                break
        return shared, None

    def hold(self, key: str) -> asyncio.Future[str | None]:
        held: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
        self.drafts[key] = held
        while len(self.drafts) > DRAFTS_HELD:
            del self.drafts[next(iter(self.drafts))]
        return held

    async def first_reply(self, req: RunRequest, key: str, held: asyncio.Future[str | None], messages: list[dict[str, Any]], deadline: float, outcome: Outcome) -> bool:
        shared: str | None = None
        done = False
        try:
            done = await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome)
            if done:
                shared = SHARED_DRAFT_NOTE.format(asked=req.user_input, draft=outcome.content.strip())
        finally:
            if shared is None and self.drafts.get(key) is held:
                del self.drafts[key]
            held.set_result(shared)
        outcome.events.append("shared draft: this reply, for later rewordings" if shared is not None else "shared draft: none written")
        return done

    async def earlier_draft(self, held: asyncio.Future[str | None], deadline: float, outcome: Outcome) -> str | None:
        try:
            draft = await asyncio.wait_for(asyncio.shield(held), max(0.01, deadline - time.monotonic() - SHARED_WAIT_RESERVE))
        except TimeoutError:
            outcome.events.append("shared draft: the draft for an earlier rewording over the same notes is not ready in time")
            return None
        outcome.events.append("shared draft: written for an earlier rewording over the same notes" if draft is not None else "shared draft: none")
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


def word_counts(pairs: list[MemoryPair]) -> Counter[str]:
    return Counter(word for pair in pairs for word in WORD_RE.findall(pair.prompt.lower()))


def cue_word(word: str, known: Counter[str]) -> str:
    lower = word.lower()
    if lower in CUE_WORDS or known[lower] > 1:
        return word
    return next((cue for cue in CUE_WORDS if typo_of(cue, lower)), word)


def cue_reading(text: str, known: Counter[str]) -> str:
    return WORD_RE.sub(lambda match: cue_word(match.group(0), known), text)


def recent_picks(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False) -> list[tuple[str, str]]:
    passages = dated_passages(notes, excerpts, labels)
    if not passages:
        return []
    others = other_paragraphs(notes, pairs)
    known = word_counts(pairs)
    misspelt: dict[tuple[str, str], bool] = {}
    if agreement:
        latest = last_in_latest_notes(notes, excerpts, phrase, others, misspelt, labels)
        if len(latest) == 2:
            return [(RECENT_NOTE_LINE, passage) for passage in latest]
    kept = [passage for passage in passages if not recurs(passage_shape(passage[1], phrase), others, misspelt)] or passages
    last = kept[-1]
    picks = [(RECENT_LINE, f"{last[0]} {last[1]}")]
    if holder:
        handed = latest_handover(notes, excerpts, known, labels)
        if handed is not None:
            picks.append((RECENT_HANDOVER_LINE, f"{handed[0]} {handed[1]}"))
        if handed is not None and HANDOVER_RE.search(handed[1]):
            after = passages[passages.index(handed) + 1:]
            stepping = next((passage for passage in reversed(after) if ACTION_CUE_RE.search(cue_reading(passage[1], known)) and FULL_NAME_RE.search(passage[1])), None)
            if stepping is not None:
                picks.append((RECENT_LATER_STEP_LINE, f"{stepping[0]} {stepping[1]}"))
        return picks
    if next_step:
        acting = next((passage for passage in reversed(passages) if ACTION_CUE_RE.search(cue_reading(passage[1], known)) and FULL_NAME_RE.search(passage[1])), None)
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


def latest_handover(notes: list[MemoryPair], excerpts: dict[str, str], known: Counter[str], labels: dict[str, str] | None = None) -> tuple[str, str] | None:
    return next((passage for passage in reversed(dated_passages(notes, excerpts, labels)) if HANDOVER_RE.search(cue_reading(passage[1], known)) and FULL_NAME_RE.search(passage[1])), None)


def handover_names(notes: list[MemoryPair], excerpts: dict[str, str], pairs: list[MemoryPair]) -> list[str]:
    handed = latest_handover(notes, excerpts, word_counts(pairs))
    return full_names(handed[1], pairs) if handed is not None else []


def email_picks(notes: list[MemoryPair], contacts: list[str], pairs: list[MemoryPair]) -> list[str]:
    marks = {pair.pair_id: mark for mark, pair in enumerate(notes, start=1)}
    out: list[str] = []
    for person in contacts:
        held = [pair for pair in person_card(person, pairs) if pair.pair_id in marks and EMAIL_ADDRESS_RE.search(pair.prompt)]
        if not held:
            continue
        latest = by_date(held)[-1]
        parts = set(person.split())
        aliases = sorted({alias for pair in pairs if person in pair.prompt and len(pair.prompt) < SHORT_RECORD_CHARS for alias in ALIAS_RE.findall(pair.prompt) if alias not in parts})
        called = "" if person in latest.prompt else next((CALLED.format(alias=alias) for alias in aliases if re.search(r"\b" + re.escape(alias) + r"\b", latest.prompt)), "")
        out.append(RECENT_EMAIL_LINE.format(person=person, called=called, passage=f"{passage_head(marks[latest.pair_id], latest)} {SPACE.sub(' ', latest.prompt).strip()}"))
    return out


def recent_view(notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], labels: dict[str, str] | None = None, holder: bool = False, next_step: bool = False, agreement: bool = False, status: bool = False, contacts: list[str] | None = None) -> str:
    picks = recent_picks(notes, excerpts, phrase, pairs, labels, holder, next_step, agreement, status)
    if not picks:
        return ""
    emails = email_picks(notes, contacts, pairs) if contacts else []
    return RECENT_HEADER + "\n" + "\n".join([line.format(phrase=phrase, passage=passage) for line, passage in picks] + emails)


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
        contacts: list[str] = []
        if CONTACT_RE.search(req.user_input):
            named = await self.named_in_reading(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
            handed = handover_names(notes, found.excerpts, pairs) if guide_records.read(req.user_input).asks_holder else []
            contacts = list(dict.fromkeys((named or []) + handed))
            notes = self.with_cards(notes, pairs, contacts or None)
        guide = guide_records.read(req.user_input)
        draft = "" if guide.asks_holder or guide.asks_figure else await self.latest_draft(req, notes, found.excerpts, phrase, pairs, deadline, outcome)
        messages = topic_messages(req, notes, found.excerpts, phrase, pairs, draft, contacts if guide.asks_contact else [])
        outcome.events.append(f"topic path phrase={phrase!r} records={len(notes)}")
        return await decide(self.engine, req, messages, self.effort, self.max_tokens, deadline, outcome, checkable=not guide_records.sequence_note(req.user_input))

    async def latest_draft(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> str:
        guide = guide_records.read(req.user_input)
        picks = recent_picks(notes, excerpts, phrase, pairs, agreement=guide.asks_disagreement, status=guide.asks_status)
        if not picks or (guide.asks_disagreement and [line for line, _ in picks] != [RECENT_NOTE_LINE, RECENT_NOTE_LINE]):
            return ""
        messages = [{"role": "system", "content": short_system(req.system_prompt, " ".join([guide_records.topic_answer_line(LATEST_SYSTEM, req.user_input), *guide_records.latest_notes(req.user_input)]))}, {"role": "user", "content": LATEST_BRIEF.format(passages="\n".join(passage for _, passage in picks), message=req.user_input)}]
        reply = await consult(self.engine.llm, self.engine.tally, req, messages, self.max_tokens, self.effort, deadline, outcome, "latest passages reading")
        written = drafted(reply)
        outcome.events.append(f"latest passages reading: {'draft' if written else 'no draft'}")
        return (reply or "").strip() if written else ""

    async def named_in_reading(self, req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], deadline: float, outcome: Outcome) -> list[str] | None:
        reply = await consult(self.engine.llm, self.engine.tally, req, topic_messages(req, notes, excerpts, phrase, pairs) + [{"role": "user", "content": PERSON_BRIEF}], self.max_tokens, self.effort, deadline, outcome, "thread reading")
        named = full_names(SPACE.sub(" ", reply or ""), pairs)
        outcome.events.append(f"thread reading named {len(named)}")
        return named or None


def topic_messages(req: RunRequest, notes: list[MemoryPair], excerpts: dict[str, str], phrase: str, pairs: list[MemoryPair], draft: str = "", contacts: list[str] | None = None) -> list[dict[str, Any]]:
    guide = guide_records.read(req.user_input)
    recent = recent_view(notes, excerpts, phrase, pairs, holder=guide.asks_holder, next_step=guide.asks_next_step, agreement=guide.asks_disagreement, status=guide.asks_status, contacts=contacts)
    beside = f"\n\n{recent}" if recent else ""
    after = f"\n\n{DRAFT_NOTE.format(draft=draft)}" if draft else ""
    user = f"{passages_view(notes, excerpts, phrase)}\n\n{NOTES_HEADER}\n\n{record_view(notes)}{beside}{after}\n\n{MESSAGE_HEADER}\n{req.user_input}"
    return [{"role": "system", "content": short_system(req.system_prompt, topic_system(req.user_input))}, {"role": "user", "content": user}]


def topic_system(message: str) -> str:
    system = guide_records.topic_decline(TOPIC_SYSTEM.replace(VALUE_VERBATIM, guide_records.words_rule(VALUE_VERBATIM, message), 1), message)
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
