from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx

from .action import ActionEngine, Outcome, TokenTally
from .action import safe_run as run_action
from .available import usable
from .typography import plain_type
from .config import Settings
from .evidence.view import answer_from_view, evidence_view
from .lane import ACTION, OWN_RECORD_CUES, RECORDS, Lane, about_own_records, alias_reading, classify, effecting, names_held_alias, own_records_question, passes_on, within_records
from .llm import LLM, build_llm, grow_call_gate
from .memory.coverage import unnamed_people
from .memory.deliberation import Deliberation
from .memory.embedding import Embedder, EmbeddingError, dense_order, fuse, record_text, text_key
from .memory.retrieval import Candidate, Retriever, UserIndex, asked_part
from .packet import build_packet, identifier_focus
from .protocol import MemoryPair, RunRequest, RunResponse, ToolDefinition
from .qtype import question_kind
from .records import RecordsEngine
from .records import safe_run as run_records
from .short import ShortPath, TopicPath, find_topic, focus_token, nicknames, short_records, topic_lead
from .store import Store
from .thint import request_kind, tool_kind
from .tools import MemoryTools, ToolExecutor

# A misspelt send or forward still asks for something to be passed on (the topic route below is for questions only).
PASS_TYPO = re.compile(r"\bforw\w*|\bsee?n[dt]\b")


def answer_form_question(request: str, tools: list[ToolDefinition]) -> bool:
    """A message worded as an answer form the qtype router reads, about the user's own records: no tool request, nothing
    passed on, and the own-records question's guards (no outside source or listed tool, no change asked for)."""
    if not question_kind(request) or tool_kind(request, [tool.name for tool in tools]):
        return False
    return not passes_on(request) and not PASS_TYPO.search(request.lower()) and within_records(request, tools)


log = logging.getLogger("harness.agent")

# Hint kinds that are not tool kinds but still ask for outside work: reading a web page, or looking a current value up
# and sending it on.
OUTSIDE_KINDS = frozenset({"web-read", "research-send"})


def bound_to_tools(request: str, tools: list[ToolDefinition]) -> bool:
    """A request whose hint kind calls a named tool, reads a web page or looks a value up and sends it: it belongs to the
    action lane, whatever phrase of it the user's notes also hold."""
    names = [tool.name for tool in tools]
    return tool_kind(request, names) or request_kind(request, names) in OUTSIDE_KINDS


class CaseRunner:
    active_cases = 0

    def __init__(self, settings: Settings, store: Store, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.store = store
        self.http = http
        self.retriever = Retriever(store, coverage_floor=settings.coverage_floor)
        self.embedder = Embedder(settings.ollama_base_url, http, settings.embed_timeout_seconds) if settings.embeddings else None
        self.order_readings: dict[str, asyncio.Future[str | None]] | None = {} if settings.short_order_cache else None
        self._default_llm: LLM | None = None

    async def embed_pairs(self, user_id: str | None, pairs: list[MemoryPair]) -> int:
        if self.embedder is None or not pairs:
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
        if self.embedder is None or not index.nodes:
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
        if req.inference_base_url and req.inference_base_url.strip() and not self.settings.mock_model:
            return build_llm(self.settings, req.inference_base_url, case_id=req.case_id)
        if self._default_llm is None:
            self._default_llm = build_llm(self.settings, None)
        return self._default_llm

    def records_engine(self, llm: LLM, executor: ToolExecutor, memory: MemoryTools, tally: TokenTally, fused: list[str] | None = None, anchors: dict[str, tuple[str, float]] | None = None) -> RecordsEngine:
        settings = self.settings
        return RecordsEngine(llm, executor, memory, tally, max_turns=settings.max_model_turns, max_tokens=settings.max_output_tokens, effort=settings.records_reasoning_effort, recall_max_tokens=settings.recall_max_tokens, recall_effort=settings.recall_reasoning_effort, packet_chars=settings.packet_char_budget, subject_discipline=settings.subject_discipline, arc=settings.arc_contiguous, worksheet=settings.worksheet, effort_high=settings.records_effort_high, thread_first=settings.thread_first, thread_reading=settings.thread_reading, closure=settings.evidence_closure, coverage=settings.coverage, link_hop=settings.link_hop, long_packet_chars=settings.long_packet_chars, meaning_records=settings.meaning_records, meaning_chars=settings.meaning_chars, meaning_order=settings.meaning_order, fused=fused, search_record_chars=settings.search_record_chars, search_long_records=settings.search_long_records, search_passes=settings.search_passes, search_temperature=settings.search_temperature, search_seed=int(settings.sampling_seed) if settings.sampling_seed else None, deliberation=Deliberation(settings.drafts, settings.draft_temperature, int(settings.sampling_seed) if settings.sampling_seed else None) if settings.deliberation else None, anchors=anchors, finder_order=settings.finder_order, follow_up=settings.follow_up, follow_up_retry=settings.follow_up_retry, act_check=settings.levers.act_check, final_check=settings.final_check)

    async def short_answer(self, req: RunRequest, lane: Lane, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if (lane.reason == "statement" or not own_records_question(req.user_input, req.tools, held=bool(focus))) and not answer_form_question(req.user_input, req.tools):
            return False
        if not focus:
            if not settings.short_story:
                return False
            if unnamed_people(index, req.user_input):
                # the records lane carries the note on who the store does hold; the topic path does not
                return False
            pairs = [node.pair for node in index.nodes.values()]
            found = find_topic(req.user_input, pairs, settings.story_min_density, settings.story_max_chars)
            if found is None:
                return False
            topic = TopicPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, max_chars=settings.story_max_chars, draft=settings.topic_draft)
            return await topic.answer(req, found, pairs, deadline, outcome)
        if not settings.short_programs:
            return False
        if not short_records(focus, settings.short_max_chars):
            return False
        token = focus_token(req.user_input, focus)
        if not token:
            return False
        short = ShortPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, readings=self.order_readings, order_max_tokens=settings.order_max_tokens, full_dates=settings.program_full_dates)
        return await short.answer(req, [cand.pair for cand in focus], token, deadline, outcome)

    async def run(self, req: RunRequest) -> RunResponse:
        started = time.monotonic()
        deadline = started + self.settings.case_budget_seconds
        tools, left_out, stayed = usable(req)
        if left_out:
            req = req.model_copy(update={"tools": tools})
        if left_out or stayed:
            log.info("case=%s catalog: %d tools kept, %d unlinked left out, %d kept as linked by the request", req.case_id, len(tools), left_out, stayed)
        CaseRunner.active_cases += 1
        gate_limit = grow_call_gate(max(self.settings.max_inflight_calls, CaseRunner.active_cases))
        memory = MemoryTools(self.store, req.user_id)
        executor = ToolExecutor(req.tool_endpoint, req.case_id, req.user_id, self.http, self.settings.tool_timeout_seconds, deadline, memory)
        tally = TokenTally()
        settings = self.settings
        levers = settings.levers
        lane = classify(req.user_input, req.tools, levers.typo_cues, preamble=levers.route_preamble, asking=levers.route_asking, anchor=levers.route_anchor, lexicon=levers.route_lexicon, operands=levers.route_operands, save=levers.route_save)
        if lane.name == RECORDS and tool_kind(req.user_input, [tool.name for tool in req.tools]):
            lane = Lane(ACTION, "tool-hint")
        if request_kind(req.user_input, [tool.name for tool in req.tools]) == "own-setting-stated":
            lane = Lane(ACTION, "setting-statement")
        outcome = Outcome()
        llm: LLM | None = None
        try:
            llm = self._llm_for(req)
            ordered, anchored = self.retriever.rank(req.user_id, req.user_input, nicknames=True)
            index = self.retriever.index(req.user_id)
            focus = identifier_focus(req.user_input, ordered)
            if lane.name != RECORDS and bound_to_tools(req.user_input, req.tools):
                pass
            elif lane.name != RECORDS and lane.reason == "live" and focus:
                lane = Lane(RECORDS, "identifier")
            elif lane.name != RECORDS and settings.short_route and focus and own_records_question(req.user_input, req.tools, held=True):
                lane = Lane(RECORDS, "identifier-held")
            elif lane.name != RECORDS and lane.reason in OWN_RECORD_CUES and about_own_records(req.user_input, req.tools, lane, index, self.retriever.question_anchors(index, req.user_input)):
                lane = Lane(RECORDS, "own-records")
            elif lane.name != RECORDS and alias_reading(req.user_input, req.tools, lane, index, nicknames([node.pair for node in index.nodes.values()])):
                lane = Lane(RECORDS, "own-records-alias")
            elif lane.name != RECORDS and settings.short_story and not focus and own_records_question(req.user_input, req.tools) and not PASS_TYPO.search(req.user_input.lower()) and find_topic(req.user_input, [node.pair for node in index.nodes.values()], settings.story_min_density, settings.story_max_chars) is not None:
                lane = Lane(RECORDS, "topic")
            elif (lane.name != RECORDS or lane.reason == "statement") and answer_form_question(req.user_input, req.tools) and (lane.reason != "live" or find_topic(req.user_input, [node.pair for node in index.nodes.values()], settings.story_min_density, settings.story_max_chars) is not None):
                lane = Lane(RECORDS, "answer-form")
            view = None
            if settings.evidence_view and not effecting(req.user_input) and not request_kind(req.user_input, [tool.name for tool in req.tools]):
                view = evidence_view(req.user_input, [node.pair for node in index.nodes.values()])
                if view is not None:
                    lane = Lane(RECORDS, "evidence")
            receipts_before = len(executor.ledger)
            # A view that gets no reply goes on to the usual paths.
            handled = view is not None and await answer_from_view(self.records_engine(llm, executor, memory, tally), req, view, [node.pair for node in index.nodes.values()], settings.short_effort, settings.short_max_tokens, deadline, outcome)
            handled = handled or lane.name == RECORDS and await self.short_answer(req, lane, focus, index, self.records_engine(llm, executor, memory, tally), deadline, outcome)
            if lane.name == RECORDS and not handled and len(executor.ledger) > receipts_before:
                # The short path's deciding turn ran tools and then ended without a reply. A fresh records run would
                # decide without those completed results (I2), so the request ends here, with no reply.
                outcome.content = ""
                outcome.answer = None
                outcome.events.append(f"short path ended after {len(executor.ledger) - receipts_before} tool results without a reply; no fresh run without them")
            elif lane.name == RECORDS and not handled:
                query = asked_part(req.user_input) if focus else req.user_input
                lexical = ordered if query == req.user_input else self.retriever.rank(req.user_id, query, nicknames=True)[0]
                try:
                    fused = await self.fused_order(req.user_id, query, lexical, index)
                except EmbeddingError as exc:
                    log.warning("case=%s embedding unavailable, lexical packet without meaning order or additions: %s", req.case_id, exc)
                    fused = None
                engine = self.records_engine(llm, executor, memory, tally, fused, self.retriever.question_anchors(index, req.user_input))
                outcome = await run_records(engine, req, ordered, anchored, {pid: node.pair for pid, node in index.nodes.items()}, deadline, index, lane.reason == "statement")
            elif lane.name != RECORDS:
                packet = build_packet(ordered, anchored, settings.packet_char_budget, settings.arc_contiguous, settings.thread_first, req.user_input, closure=settings.evidence_closure, index=index if settings.link_hop else None)
                lead = ""
                pairs = [node.pair for node in index.nodes.values()]
                if settings.action_topic and not focus and (own_records_question(req.user_input, req.tools) or (settings.action_topic_alias and names_held_alias(req.user_input, req.tools, index, nicknames(pairs)))):
                    packet, lead = topic_lead(req.user_input, packet, pairs, settings.story_min_density, settings.story_max_chars)
                engine = ActionEngine(llm, executor, memory, tally, max_turns=settings.action_max_turns, max_tokens=settings.action_max_tokens, effort=settings.action_reasoning_effort, levers=settings.levers)
                outcome = await run_action(engine, req, packet, deadline, lane.reason, lead)
        except Exception:
            log.exception("case=%s unexpected failure", req.case_id)
            raise
        finally:
            CaseRunner.active_cases -= 1
            if llm is not None and llm is not self._default_llm:
                await llm.aclose()
        latency_ms = int((time.monotonic() - started) * 1000)
        log.info("case=%s user=%s lane=%s:%s observed=%d host=%d memory=%d model_calls=%d answer=%r ms=%d gate=%d events=%s", req.case_id, req.user_id, lane.name, lane.reason, len(executor.observed), outcome.host_calls, outcome.memory_calls, outcome.model_calls, outcome.answer, latency_ms, gate_limit, outcome.events)
        return RunResponse(final_text=plain_type(outcome.content.strip()), tool_calls=executor.observed, prompt_tokens=tally.prompt, output_tokens=tally.output, latency_ms=latency_ms, answer=None if outcome.answer is None else plain_type(outcome.answer), abstain=False)
