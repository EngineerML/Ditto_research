from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .action import ActionEngine, Outcome, TokenTally
from .action import safe_run as run_action
from .typography import plain_type
from .config import Settings
from .guide_tools import setting_lead
from .request_kinds import request_kinds
from .revocation import Revocation
from .lane import ACTION, RECORDS, Lane, about_own_records, classify, names_held_alias, own_records_question
from .lane import effecting, main_clause
from .llm import LLM, build_llm, grow_call_gate
from .memory.deliberation import Deliberation
from .memory.embedding import Embedder, EmbeddingError, dense_order, fuse, record_text, text_key
from .memory.retrieval import Candidate, Retriever, UserIndex, asked_part
from .packet import build_packet, held_identifier, identifier_focus
from .protocol import MemoryPair, RunRequest, RunResponse, normalize_user_id
from .records import RecordsEngine
from .records import safe_run as run_records
from .guide_spelling import read_form
from .guide_records import asks_account_figure, asks_contact_detail, asks_handle, asks_order, asks_stays_total, story_step_question
from .short import ShortPath, TopicPath, answer_from_view, evidence_view, find_topic, named_in, same_file, note_words, repeat_reply, same_notes, same_question, setting_reading, receipt_lead, recipient_lead, focus_token, nicknames, people_lead, scratchpad_lead, short_records, topic_lead
from .store import Store
from .tools import MemoryTools, ToolExecutor

log = logging.getLogger("harness.agent")
SAME_QUESTION_RESERVE = 45.0




class CaseRunner:
    active_cases = 0

    def __init__(self, settings: Settings, store: Store, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.store = store
        self.http = http
        self.retriever = Retriever(store, coverage_floor=settings.coverage_floor)
        self.embedder = Embedder(settings.ollama_base_url, http, settings.embed_timeout_seconds)
        self.short_drafts: dict[str, asyncio.Future[str | None]] = {}
        self.asked_before: dict[str, list[tuple[str, frozenset[str], frozenset[str], str, asyncio.Future[str]]]] = {}
        self._default_llm: LLM | None = None

    async def embed_pairs(self, user_id: str | None, pairs: list[MemoryPair]) -> int:
        if not pairs:
            return 0
        texts = {text_key(record_text(pair)): record_text(pair) for pair in pairs}
        held = self.store.vectors(user_id, list(texts))
        missing = [key for key in texts if key not in held]
        if not missing:
            return 0
        vectors = await self.embedder.embed([texts[key] for key in missing])
        self.store.put_vectors(user_id, dict(zip(missing, vectors)))
        return len(missing)

    async def fused_order(self, user_id: str | None, question: str, ordered: list[Candidate], index: UserIndex) -> list[str] | None:
        if not index.nodes:
            return None
        pairs = [node.pair for node in index.nodes.values()]
        held = self.store.vectors(user_id, [text_key(record_text(pair)) for pair in pairs])
        missing = [pair for pair in pairs if text_key(record_text(pair)) not in held]
        vectors = await self.embedder.embed([question] + [record_text(pair) for pair in missing])
        fresh = {text_key(record_text(pair)): vector for pair, vector in zip(missing, vectors[1:])}
        self.store.put_vectors(user_id, fresh)
        held.update(fresh)
        return fuse([cand.pair.pair_id for cand in ordered], dense_order(vectors[0], pairs, held))

    def _llm_for(self, req: RunRequest) -> LLM:
        if req.inference_base_url and req.inference_base_url.strip():
            return build_llm(self.settings, req.inference_base_url)
        if self._default_llm is None:
            self._default_llm = build_llm(self.settings, None)
        return self._default_llm

    def records_engine(self, llm: LLM, executor: ToolExecutor, memory: MemoryTools, tally: TokenTally, fused: list[str] | None = None, anchors: dict[str, tuple[str, float]] | None = None) -> RecordsEngine:
        settings = self.settings
        return RecordsEngine(llm, executor, memory, tally, max_turns=settings.max_model_turns, max_tokens=settings.max_output_tokens, effort=settings.records_reasoning_effort, recall_max_tokens=settings.recall_max_tokens, recall_effort=settings.recall_reasoning_effort, packet_chars=settings.packet_char_budget, long_packet_chars=settings.long_packet_chars, meaning_records=settings.meaning_records, meaning_chars=settings.meaning_chars, fused=fused, search_record_chars=settings.search_record_chars, search_long_records=settings.search_long_records, search_passes=settings.search_passes, search_temperature=settings.search_temperature, search_seed=settings.sampling_seed, deliberation=Deliberation(settings.drafts, settings.draft_temperature, settings.sampling_seed), anchors=anchors)

    async def short_answer(self, req: RunRequest, lane: Lane, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if not (story_step_question(req.user_input) and not focus) and (lane.reason == "statement" or not own_records_question(req.user_input, req.tools, carried=bool(focus))):
            return False
        if not focus:
            pairs = [node.pair for node in index.nodes.values()]
            found = find_topic(req.user_input, pairs, settings.story_min_density, settings.story_max_chars)
            if found is None:
                return False
            topic = TopicPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, max_chars=settings.story_max_chars)
            return await topic.answer(req, found, pairs, deadline, outcome)
        if not short_records(focus, settings.short_max_chars):
            return False
        token = focus_token(req.user_input, focus)
        if not token:
            return False
        short = ShortPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, drafts=self.short_drafts)
        return await short.answer(req, [cand.pair for cand in focus], token, deadline, outcome)

    async def stored_detail_topic(self, req: RunRequest, lane: Lane, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if focus or lane.reason != "stored-detail" or own_records_question(req.user_input, req.tools):
            return False
        pairs = [node.pair for node in index.nodes.values()]
        found = find_topic(req.user_input, pairs, settings.story_min_density, settings.story_max_chars)
        if found is None:
            return False
        outcome.events.append("topic path for a stored detail")
        topic = TopicPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, max_chars=settings.story_max_chars)
        return await topic.answer(req, found, pairs, deadline, outcome)

    async def run(self, req: RunRequest) -> RunResponse:
        started = time.monotonic()
        deadline = started + self.settings.case_budget_seconds
        CaseRunner.active_cases += 1
        gate_limit = grow_call_gate(max(self.settings.max_inflight_calls, CaseRunner.active_cases))
        memory = MemoryTools(self.store, req.user_id)
        executor = ToolExecutor(req.tool_endpoint, req.case_id, req.user_id, self.http, self.settings.tool_timeout_seconds, deadline, memory)
        tally = TokenTally()
        settings = self.settings
        lane = classify(main_clause(req.user_input), req.tools)
        outcome = Outcome()
        answering: asyncio.Future[str] | None = None
        llm: LLM | None = None
        try:
            llm = self._llm_for(req)
            executor.revocation = Revocation(llm, tally, req, deadline)
            ordered, anchored = self.retriever.rank(req.user_id, req.user_input)
            index = self.retriever.index(req.user_id)
            focus = identifier_focus(req.user_input, ordered)
            kinds = request_kinds(req.user_input, [tool.name for tool in req.tools])
            if lane.name != RECORDS and lane.reason == "live" and focus:
                lane = Lane(RECORDS, "identifier")
            elif lane.name != RECORDS and focus and own_records_question(req.user_input, req.tools, carried=True):
                lane = Lane(RECORDS, "identifier-held")
            elif lane.name != RECORDS and lane.reason == "live" and about_own_records(req.user_input, req.tools, lane, index, self.retriever.question_anchors(index, req.user_input)):
                lane = Lane(RECORDS, "own-records")
            elif lane.name != RECORDS and lane.reason == "default" and own_records_question(req.user_input, req.tools, working=True) and held_identifier(req.user_input, ordered):
                lane = Lane(RECORDS, "identifier-read")
            elif lane.name != RECORDS and not kinds and not focus and own_records_question(req.user_input, req.tools) and find_topic(req.user_input, [node.pair for node in index.nodes.values()], settings.story_min_density, settings.story_max_chars) is not None:
                lane = Lane(RECORDS, "topic")
            elif lane.name != RECORDS and not kinds and not focus and story_step_question(req.user_input) and (asks_order(req.user_input) or not effecting(req.user_input)) and find_topic(req.user_input, [node.pair for node in index.nodes.values()], settings.story_min_density, settings.story_max_chars):
                lane = Lane(RECORDS, "topic")
            elif lane.name != RECORDS and not kinds and not focus and (asks_handle(req.user_input) or asks_stays_total(req.user_input) or asks_account_figure(req.user_input) or asks_contact_detail(req.user_input)):
                lane = Lane(RECORDS, "handle")
            elif lane.name != RECORDS and not kinds and own_records_question(req.user_input, req.tools) and any(kind == "q" for kind, _ in self.retriever.question_anchors(index, req.user_input).values()):
                lane = Lane(RECORDS, "quoted")
            if lane.name == RECORDS and kinds:
                lane = Lane(ACTION, "guided")
            view = evidence_view(req.user_input, [node.pair for node in index.nodes.values()]) if not kinds else None
            if view is not None:
                lane = Lane(RECORDS, "evidence")
            short_engine = self.records_engine(llm, executor, memory, tally)
            # The same question over the same notes, asked again in other words or under another file code holding the same words, gets
            # its earlier reply through the model. Not a request to do something: that goes to its tools every time.
            token = "" if effecting(req.user_input) else focus_token(req.user_input, focus) if focus and not kinds and lane.name == RECORDS else ""
            handled = False
            if token:
                asked = read_form(asked_part(req.user_input)).lower()
                file_key, _ = same_file(req.user_input, [node.pair for node in index.nodes.values()])
                words = frozenset({file_key}) if file_key else note_words([cand.pair for cand in focus], token)
                named = named_in(req.user_input, token)
                seen = self.asked_before.setdefault(normalize_user_id(req.user_id), [])
                earlier = next((held for held in seen if held[2] == named and same_question(asked, held[0]) and same_notes(words, held[1])), None)
                if earlier is None:
                    answering = asyncio.get_running_loop().create_future()
                    seen.append((asked, words, named, req.user_input, answering))
                else:
                    try:
                        reply = await asyncio.wait_for(asyncio.shield(earlier[4]), max(0.01, deadline - time.monotonic() - SAME_QUESTION_RESERVE))
                    except TimeoutError:
                        reply = ""
                    handled = bool(reply) and await repeat_reply(short_engine, req, earlier[3], reply, settings.short_max_tokens, deadline, outcome, bool(file_key))
                    if handled:
                        lane = Lane(RECORDS, "same-question")
            handled = handled or view is not None and await answer_from_view(short_engine, req, view, [node.pair for node in index.nodes.values()], settings.short_effort, settings.short_max_tokens, deadline, outcome)
            handled = handled or lane.name == RECORDS and await self.short_answer(req, lane, focus, index, short_engine, deadline, outcome)
            handled = handled or (lane.name == RECORDS and await self.stored_detail_topic(req, lane, focus, index, short_engine, deadline, outcome))
            if lane.name == RECORDS and not handled:
                query = asked_part(req.user_input) if focus else req.user_input
                lexical = ordered if query == req.user_input else self.retriever.rank(req.user_id, query)[0]
                try:
                    fused = await self.fused_order(req.user_id, query, lexical, index)
                except EmbeddingError as exc:
                    log.warning("case=%s embedding unavailable, lexical packet without meaning order or additions: %s", req.case_id, exc)
                    fused = None
                engine = self.records_engine(llm, executor, memory, tally, fused, self.retriever.question_anchors(index, req.user_input))
                outcome = await run_records(engine, req, ordered, anchored, {pid: node.pair for pid, node in index.nodes.items()}, deadline, index, lane.reason == "statement", short_engine.carried)
            elif lane.name != RECORDS:
                packet = build_packet(ordered, anchored, settings.packet_char_budget, req.user_input, index)
                lead = ""
                pairs = [node.pair for node in index.nodes.values()]
                if not focus and (own_records_question(req.user_input, req.tools) or names_held_alias(req.user_input, req.tools, index, nicknames(pairs))):
                    packet, lead = topic_lead(req.user_input, packet, pairs, settings.story_min_density, settings.story_max_chars)
                if "disposable_note" in kinds or "workflow_if_missing" in kinds:
                    packet, people = people_lead(req.user_input, packet, pairs)
                    lead = "\n\n".join(part for part in (lead, people) if part)
                if "disposable_note" in kinds:
                    packet, receipt = receipt_lead(req.user_input, packet, pairs)
                    lead = "\n\n".join(part for part in (receipt, lead) if part)
                if "send_to_them" in kinds:
                    packet, recipient = recipient_lead(req.user_input, packet, pairs)
                    lead = "\n\n".join(part for part in (recipient, lead) if part)
                if "handoff_correction" in kinds:
                    packet, pad = scratchpad_lead(req.user_input, packet, pairs)
                    lead = "\n\n".join(part for part in (lead, pad) if part)
                if "setting_check" in kinds:
                    notes = setting_lead(req.user_input, pairs)
                    reading = await setting_reading(short_engine, req, notes, deadline, outcome) if notes else ""
                    lead = "\n\n".join(part for part in (lead, notes, reading) if part)
                engine = ActionEngine(llm, executor, memory, tally, max_turns=settings.action_max_turns, max_tokens=settings.action_max_tokens, effort=settings.action_reasoning_effort)
                outcome = await run_action(engine, req, packet, deadline, lane.reason, lead)
        except Exception:
            log.exception("case=%s unexpected failure", req.case_id)
            raise
        finally:
            if answering is not None and not answering.done():
                answering.set_result(outcome.content.strip())
            CaseRunner.active_cases -= 1
            if llm is not None and llm is not self._default_llm:
                await llm.aclose()
        latency_ms = int((time.monotonic() - started) * 1000)
        log.info("case=%s user=%s lane=%s:%s observed=%d host=%d memory=%d model_calls=%d answer=%r ms=%d gate=%d events=%s", req.case_id, req.user_id, lane.name, lane.reason, len(executor.observed), outcome.host_calls, outcome.memory_calls, outcome.model_calls, outcome.answer, latency_ms, gate_limit, outcome.events)
        return RunResponse(final_text=plain_type(outcome.content.strip()), tool_calls=executor.observed, prompt_tokens=tally.prompt, output_tokens=tally.output, latency_ms=latency_ms, answer=None if outcome.answer is None else plain_type(outcome.answer))
