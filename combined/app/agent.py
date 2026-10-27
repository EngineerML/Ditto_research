from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .action import ActionEngine, Outcome, TokenTally
from .action import safe_run as run_action
from .typography import plain_type
from .config import Settings
from .llm import LLM, build_llm, grow_call_gate
from .memory.deliberation import Deliberation
from .memory.embedding import Embedder, EmbeddingError, dense_order, fuse, record_text, text_key
from .memory.retrieval import Candidate, Retriever, UserIndex, asked_part
from .ours import lane as ours
from .ours.guidance import moves_to_action
from .ours.meaning import IntentBank
from .packet import build_packet, fused_rank, identifier_focus, refill
from .protocol import MemoryPair, RunRequest, RunResponse
from .records import RecordsEngine
from .records import safe_run as run_records
from .short import ShortPath, TopicPath, find_topic, focus_token, short_records, topic_lead
from .store import Store
from .tools import MemoryTools, ToolExecutor

log = logging.getLogger("harness.agent")

# Routing and record selection come from our harness (app/ours, harness/app/engine/agent.py on
# harness/hades-v6-base); everything after them, the lanes' prompt loops included, is dan0l v24's.
MEANING_SURE = 0.85
IDENTIFIER_REASONS = frozenset({"identifier", "identifier-held"})
TEXT_HITS = 40


class CaseRunner:
    active_cases = 0

    def __init__(self, settings: Settings, store: Store, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.store = store
        self.http = http
        self.retriever = Retriever(store, coverage_floor=settings.coverage_floor)
        self.embedder = Embedder(settings.ollama_base_url, http, settings.embed_timeout_seconds)
        self.intents = IntentBank()
        self.order_readings: dict[str, asyncio.Future[str | None]] = {}
        self.short_drafts: dict[str, asyncio.Future[str | None]] = {}
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

    async def fused_order(self, user_id: str | None, question: str, ordered: list[Candidate], index: UserIndex) -> tuple[list[str], list[str]] | None:
        """(lexical and meaning orders fused, meaning order alone)."""
        if not index.nodes:
            return None
        pairs = [node.pair for node in index.nodes.values()]
        held = self.store.vectors(user_id, [text_key(record_text(pair)) for pair in pairs])
        missing = [pair for pair in pairs if text_key(record_text(pair)) not in held]
        vectors = await self.embedder.embed([question] + [record_text(pair) for pair in missing])
        fresh = {text_key(record_text(pair)): vector for pair, vector in zip(missing, vectors[1:])}
        self.store.put_vectors(user_id, fresh)
        held.update(fresh)
        dense = dense_order(vectors[0], pairs, held)
        return fuse([cand.pair.pair_id for cand in ordered], dense), dense

    def ranking_orders(self, user_id: str | None, question: str, ordered: list[Candidate], dense: list[str]) -> list[tuple[list[str], float]]:
        hits = [hit.pair.pair_id for hit in self.store.search(user_id, question, limit=TEXT_HITS)]
        return [([cand.pair.pair_id for cand in ordered], 1.0), (dense, 1.0), (hits, 0.5)]

    def _llm_for(self, req: RunRequest) -> LLM:
        if req.inference_base_url and req.inference_base_url.strip():
            return build_llm(self.settings, req.inference_base_url)
        if self._default_llm is None:
            self._default_llm = build_llm(self.settings, None)
        return self._default_llm

    def records_engine(self, llm: LLM, executor: ToolExecutor, memory: MemoryTools, tally: TokenTally, fused: list[str] | None = None, anchors: dict[str, tuple[str, float]] | None = None, rank_orders: list[tuple[list[str], float]] | None = None) -> RecordsEngine:
        settings = self.settings
        return RecordsEngine(llm, executor, memory, tally, max_turns=settings.max_model_turns, max_tokens=settings.max_output_tokens, effort=settings.records_reasoning_effort, recall_max_tokens=settings.recall_max_tokens, recall_effort=settings.recall_reasoning_effort, packet_chars=settings.packet_char_budget, long_packet_chars=settings.long_packet_chars, meaning_records=settings.meaning_records, meaning_chars=settings.meaning_chars, fused=fused, search_record_chars=settings.search_record_chars, search_long_records=settings.search_long_records, search_passes=settings.search_passes, search_temperature=settings.search_temperature, search_seed=settings.sampling_seed, deliberation=Deliberation(settings.drafts, settings.draft_temperature, settings.sampling_seed), anchors=anchors, rank_orders=rank_orders)

    def choose_lane(self, req: RunRequest, index: UserIndex, focus: list[Candidate]) -> tuple[ours.Lane, str]:
        """Our word rules on the request with misspelled cue words mended (for routing only), and their overrides."""
        settings = self.settings
        named = {word for tool in req.tools for word in ours.tokens(tool.name.replace("_", " ") + " " + (tool.description or ""))}
        routed = ours.mend_cues(req.user_input, req.tools, lambda word: bool(index.df[word]) or word in named)
        lane = ours.classify(routed, req.tools, True)
        anchors = self.retriever.question_anchors(index, req.user_input)
        if lane.name != ours.RECORDS and lane.reason == "live" and focus:
            lane = ours.Lane(ours.RECORDS, "identifier")
        elif lane.name != ours.RECORDS and focus and ours.own_records_question(routed, req.tools):
            lane = ours.Lane(ours.RECORDS, "identifier-held")
        elif lane.name != ours.RECORDS and lane.reason == "live" and ours.about_own_records(routed, req.tools, lane, index, anchors):
            lane = ours.Lane(ours.RECORDS, "own-records")
        elif lane.name == ours.ACTION and lane.reason in ours.OVERRIDABLE_REASONS:
            pairs = [node.pair for node in index.nodes.values()]
            topic = find_topic(req.user_input, pairs, settings.story_min_density, settings.story_max_chars) is not None
            held = lane.reason != "live" and (ours.held_in_records(routed, req.tools, index, anchors) or bool(ours.OWN_THING.search(routed)))
            if (focus or topic or held) and (ours.records_question(routed, req.tools) or (topic and ours.elliptical(routed))):
                lane = ours.Lane(ours.RECORDS, "own-question")
        if lane.name == ours.RECORDS and lane.reason in ("question", "asked") and ours.product_question(routed):
            lane = ours.Lane(ours.ACTION, "product-question")
        return lane, routed

    async def meaning_lane(self, req: RunRequest, lane: ours.Lane, routed: str) -> ours.Lane:
        if lane.reason in IDENTIFIER_REASONS:
            return lane
        sense = await self.intents.lane(self.embedder, req.user_input)
        if sense is None or sense[1] < MEANING_SURE or sense[0] == lane.name:
            return lane
        if sense[0] == ours.RECORDS:
            if ours.keeps_action(routed):
                return lane
            return ours.Lane(ours.RECORDS, "statement" if ours.tells_without_asking(routed) else "meaning")
        if ours.keeps_records(routed, req.tools):
            return lane
        return ours.Lane(ours.ACTION, "meaning")

    async def short_answer(self, req: RunRequest, lane: ours.Lane, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if lane.reason == "statement" or not ours.own_records_question(req.user_input, req.tools):
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
        short = ShortPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, readings=self.order_readings, order_max_tokens=settings.order_max_tokens, drafts=self.short_drafts)
        return await short.answer(req, [cand.pair for cand in focus], token, deadline, outcome)

    async def stored_detail_topic(self, req: RunRequest, lane: ours.Lane, routed: str, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if focus or lane.reason == "statement" or not ours.asks_stored_detail(routed):
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
        lane = ours.Lane(ours.ACTION, "unrouted")
        outcome = Outcome()
        llm: LLM | None = None
        try:
            llm = self._llm_for(req)
            ordered, anchored = self.retriever.rank(req.user_id, req.user_input)
            index = self.retriever.index(req.user_id)
            focus = identifier_focus(req.user_input, ordered)
            lane, routed = self.choose_lane(req, index, focus)
            lane = await self.meaning_lane(req, lane, routed)
            if lane.name == ours.RECORDS and moves_to_action(req.user_input, req.tools):
                lane = ours.Lane(ours.ACTION, "guided")
            pairs_by_id = {pid: node.pair for pid, node in index.nodes.items()}
            handled = lane.name == ours.RECORDS and await self.short_answer(req, lane, focus, index, self.records_engine(llm, executor, memory, tally), deadline, outcome)
            handled = handled or (lane.name == ours.RECORDS and await self.stored_detail_topic(req, lane, routed, focus, index, self.records_engine(llm, executor, memory, tally), deadline, outcome))
            if lane.name == ours.RECORDS and not handled:
                query = asked_part(req.user_input) if focus else req.user_input
                lexical = ordered if query == req.user_input else self.retriever.rank(req.user_id, query)[0]
                try:
                    fused, dense = await self.fused_order(req.user_id, query, lexical, index) or (None, [])
                except EmbeddingError as exc:
                    log.warning("case=%s embedding unavailable, lexical packet without meaning order or additions: %s", req.case_id, exc)
                    fused, dense = None, []
                engine = self.records_engine(llm, executor, memory, tally, fused, self.retriever.question_anchors(index, req.user_input), self.ranking_orders(req.user_id, req.user_input, ordered, dense))
                outcome = await run_records(engine, req, ordered, anchored, pairs_by_id, deadline, index, lane.reason == "statement")
            elif lane.name != ours.RECORDS:
                packet = build_packet(ordered, anchored, settings.packet_char_budget, req.user_input, index)
                lead = ""
                pairs = [node.pair for node in index.nodes.values()]
                if not focus and ours.own_records_question(req.user_input, req.tools):
                    packet, lead = topic_lead(req.user_input, packet, pairs, settings.story_min_density, settings.story_max_chars)
                if packet.records:
                    try:
                        dense = (await self.fused_order(req.user_id, req.user_input, ordered, index) or (None, []))[1]
                    except EmbeddingError as exc:
                        log.warning("case=%s embedding unavailable, action packet refilled without meaning: %s", req.case_id, exc)
                        dense = []
                    better = fused_rank(self.ranking_orders(req.user_id, req.user_input, ordered, dense) + [([c.pair.pair_id for c in packet.records], 1.0)])
                    packet = refill(packet, better, pairs_by_id, settings.search_record_chars)
                engine = ActionEngine(llm, executor, memory, tally, max_turns=settings.action_max_turns, max_tokens=settings.action_max_tokens, effort=settings.action_reasoning_effort)
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
        return RunResponse(final_text=plain_type(outcome.content.strip()), tool_calls=executor.observed, prompt_tokens=tally.prompt, output_tokens=tally.output, latency_ms=latency_ms, answer=None if outcome.answer is None else plain_type(outcome.answer))
