from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

from app.answer import plain_hyphens
from app.audit import CURRENT, Journal
from app.engine.action import ActionEngine
from app.engine.state import Outcome, TokenTally
from app.engine.action import safe_run as run_action
from app.config import Settings
from app.routing.lane import ACTION, RECORDS, Lane, about_own_records, classify, own_records_question, tells_without_asking
from app.routing.meaning import IntentBank
from app.llm import LLM, build_llm, grow_call_gate
from app.memory.deliberation import Deliberation
from app.memory.embedding import Embedder, EmbeddingError, dense_order, fuse, record_text, text_key
from app.memory.retrieval import Candidate, Retriever, UserIndex, asked_part
from app.memory.packet import build_packet, fused_rank, identifier_focus, refill, swap_in, widen
from app.protocol import MemoryPair, RunRequest, RunResponse
from app.engine.records import RecordsEngine
from app.engine.records import safe_run as run_records
from app.engine.short import ShortPath, TopicPath, find_topic, focus_token, short_records, topic_lead
from app.memory.store import Store
from app.memory.tools import MemoryTools
from app.tooling.executor import ToolExecutor

log = logging.getLogger("harness.agent")
SWAP_TEXT_HITS = 40
RERANK_MODES = ("refill", "swap")


class CaseRunner:
    active_cases = 0

    def __init__(self, settings: Settings, store: Store, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.store = store
        self.http = http
        self.retriever = Retriever(store, coverage_floor=settings.coverage_floor)
        self.embedder = Embedder(settings.ollama_base_url, http, settings.embed_timeout_seconds) if settings.embeddings else None
        self.order_readings: dict[str, asyncio.Future[str | None]] | None = {} if settings.short_order_cache else None
        self.intents = IntentBank() if settings.meaning_route and self.embedder is not None else None
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

    async def fused_order(self, user_id: str | None, question: str, ordered: list[Candidate], index: UserIndex) -> tuple[list[str], list[str]] | None:
        """(lexical and meaning orders fused, meaning order alone)."""
        if self.embedder is None or not index.nodes:
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

    def widening(self, user_id: str | None, question: str, dense: list[str], anchored: bool) -> list[str]:
        """Records to add beside the packet: the closest by meaning, then the best full-text matches.

        Nothing is added when the request names nothing the records hold (greetings, general questions) and
        `widen_anchored` is on: there the extra records only lengthen the prompt."""
        if self.settings.select_mode != "widen" or not self.settings.widen or (self.settings.widen_anchored and not anchored):
            return []
        hits = [hit.pair.pair_id for hit in self.store.search(user_id, question, limit=self.settings.widen_text)]
        return list(dict.fromkeys(dense[: self.settings.widen_dense] + hits))

    def ranking_orders(self, user_id: str | None, question: str, ordered: list[Candidate], dense: list[str]) -> list[tuple[list[str], float]]:
        """The orders a swap fuses with the packet's own: the retriever's, meaning, and full-text (at half weight)."""
        hits = [hit.pair.pair_id for hit in self.store.search(user_id, question, limit=SWAP_TEXT_HITS)]
        return [([cand.pair.pair_id for cand in ordered], 1.0), (dense, 1.0), (hits, 0.5)]

    async def meaning_lane(self, req: RunRequest, lane: Lane) -> Lane:
        if self.intents is None or self.embedder is None:
            return lane
        sense = await self.intents.lane(self.embedder, req.user_input)
        if sense is None or sense[1] < self.settings.meaning_sure or sense[0] == lane.name:
            return lane
        if sense[0] == RECORDS:
            # A message the meaning router moves to the records lane that asks nothing ("Heads up — I take my coffee
            # black") is a statement there: no recall search, and a lasting fact is saved.
            return Lane(RECORDS, "statement" if tells_without_asking(req.user_input) else "meaning")
        return Lane(ACTION, "meaning")

    def _llm_for(self, req: RunRequest) -> LLM:
        if req.inference_base_url and req.inference_base_url.strip() and not self.settings.mock_model:
            return build_llm(self.settings, req.inference_base_url)
        if self._default_llm is None:
            self._default_llm = build_llm(self.settings, None)
        return self._default_llm

    def records_engine(self, llm: LLM, executor: ToolExecutor, memory: MemoryTools, tally: TokenTally, fused: list[str] | None = None, anchors: dict[str, tuple[str, float]] | None = None, extra: list[str] | None = None, rank_orders: list[tuple[list[str], float]] | None = None) -> RecordsEngine:
        settings = self.settings
        return RecordsEngine(llm, executor, memory, tally, max_turns=settings.max_model_turns, max_tokens=settings.max_output_tokens, effort=settings.records_reasoning_effort, recall_max_tokens=settings.recall_max_tokens, recall_effort=settings.recall_reasoning_effort, packet_chars=settings.packet_char_budget, subject_discipline=settings.subject_discipline, arc=settings.arc_contiguous, worksheet=settings.worksheet, effort_high=settings.records_effort_high, thread_first=settings.thread_first, thread_reading=settings.thread_reading, closure=settings.evidence_closure, coverage=settings.coverage, link_hop=settings.link_hop, long_packet_chars=settings.long_packet_chars, meaning_records=settings.meaning_records, meaning_chars=settings.meaning_chars, meaning_order=settings.meaning_order, fused=fused, search_record_chars=settings.search_record_chars, search_long_records=settings.search_long_records, search_passes=settings.search_passes, search_temperature=settings.search_temperature, search_seed=int(settings.sampling_seed) if settings.sampling_seed else None, deliberation=Deliberation(settings.drafts, settings.draft_temperature, int(settings.sampling_seed) if settings.sampling_seed else None) if settings.deliberation else None, anchors=anchors, finder_order=settings.finder_order, follow_up=settings.follow_up, follow_up_retry=settings.follow_up_retry, extra=extra, widen_chars=settings.widen_chars, rank_orders=rank_orders, swap_top=settings.swap_top, select_mode=settings.select_mode)

    async def short_answer(self, req: RunRequest, lane: Lane, focus: list[Candidate], index: UserIndex, engine: RecordsEngine, deadline: float, outcome: Outcome) -> bool:
        settings = self.settings
        if lane.reason == "statement" or not own_records_question(req.user_input, req.tools):
            return False
        if not focus:
            if not settings.short_story:
                return False
            pairs = [node.pair for node in index.nodes.values()]
            found = find_topic(req.user_input, pairs, settings.story_min_density, settings.story_max_chars)
            if found is None:
                return False
            topic = TopicPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, max_chars=settings.story_max_chars, draft=settings.topic_draft, decide_effort=settings.topic_decide_effort)
            return await topic.answer(req, found, pairs, deadline, outcome)
        if not settings.short_programs:
            return False
        if not short_records(focus, settings.short_max_chars):
            return False
        token = focus_token(req.user_input, focus)
        if not token:
            return False
        short = ShortPath(engine, effort=settings.short_effort, max_tokens=settings.short_max_tokens, readings=self.order_readings, order_max_tokens=settings.order_max_tokens, full_dates=settings.program_full_dates, shared_draft=settings.short_shared_draft)
        return await short.answer(req, [cand.pair for cand in focus], token, deadline, outcome)

    async def run(self, req: RunRequest) -> RunResponse:
        path = os.environ.get("DITTOBENCH_COMPLETION_LOG")
        journal = Journal(req, self.store.all_pairs(req.user_id)) if path else None
        token = CURRENT.set(journal)
        try:
            return await self._run(req)
        finally:
            CURRENT.reset(token)
            if journal is not None:
                try:
                    journal.write(path)
                except Exception:
                    log.exception("case=%s completion journal could not be written", req.case_id)

    async def _run(self, req: RunRequest) -> RunResponse:
        started = time.monotonic()
        deadline = started + self.settings.case_budget_seconds
        CaseRunner.active_cases += 1
        gate_limit = grow_call_gate(max(self.settings.max_inflight_calls, CaseRunner.active_cases))
        memory = MemoryTools(self.store, req.user_id, req.tools)
        executor = ToolExecutor(req.tool_endpoint, req.case_id, req.user_id, self.http, self.settings.tool_timeout_seconds, deadline, memory)
        tally = TokenTally()
        settings = self.settings
        levers = settings.levers
        lane = classify(req.user_input, req.tools, levers.typo_cues, preamble=levers.route_preamble, asking=levers.route_asking, anchor=levers.route_anchor, lexicon=levers.route_lexicon, operands=levers.route_operands, save=levers.route_save)
        outcome = Outcome()
        llm: LLM | None = None
        try:
            llm = self._llm_for(req)
            ordered, anchored = self.retriever.rank(req.user_id, req.user_input)
            index = self.retriever.index(req.user_id)
            focus = identifier_focus(req.user_input, ordered)
            if lane.name != RECORDS and lane.reason == "live" and focus:
                lane = Lane(RECORDS, "identifier")
            elif lane.name != RECORDS and settings.short_route and focus and own_records_question(req.user_input, req.tools):
                lane = Lane(RECORDS, "identifier-held")
            elif lane.name != RECORDS and lane.reason == "live" and about_own_records(req.user_input, req.tools, lane, index, self.retriever.question_anchors(index, req.user_input)):
                lane = Lane(RECORDS, "own-records")
            lane = await self.meaning_lane(req, lane)
            handled = lane.name == RECORDS and await self.short_answer(req, lane, focus, index, self.records_engine(llm, executor, memory, tally), deadline, outcome)
            if lane.name == RECORDS and not handled:
                query = asked_part(req.user_input) if focus else req.user_input
                lexical = ordered if query == req.user_input else self.retriever.rank(req.user_id, query)[0]
                try:
                    orders = await self.fused_order(req.user_id, query, lexical, index)
                except EmbeddingError as exc:
                    log.warning("case=%s embedding unavailable, lexical packet without meaning order or additions: %s", req.case_id, exc)
                    orders = None
                fused, dense = orders if orders is not None else (None, [])
                extra = self.widening(req.user_id, req.user_input, dense, anchored)
                rank_orders = self.ranking_orders(req.user_id, req.user_input, ordered, dense) if settings.select_mode in RERANK_MODES else None
                engine = self.records_engine(llm, executor, memory, tally, fused, self.retriever.question_anchors(index, req.user_input), extra, rank_orders)
                outcome = await run_records(engine, req, ordered, anchored, {pid: node.pair for pid, node in index.nodes.items()}, deadline, index, lane.reason == "statement")
            elif lane.name != RECORDS:
                packet = build_packet(ordered, anchored, settings.packet_char_budget, settings.arc_contiguous, settings.thread_first, req.user_input, closure=settings.evidence_closure, index=index if settings.link_hop else None)
                lead = ""
                if settings.action_topic and not focus and own_records_question(req.user_input, req.tools):
                    packet, lead = topic_lead(req.user_input, packet, [node.pair for node in index.nodes.values()], settings.story_min_density, settings.story_max_chars)
                selecting = settings.select_mode in RERANK_MODES or (settings.select_mode == "widen" and settings.widen and (anchored or not settings.widen_anchored))
                if selecting and packet.records:
                    try:
                        orders = await self.fused_order(req.user_id, req.user_input, ordered, index)
                    except EmbeddingError as exc:
                        log.warning("case=%s embedding unavailable, action packet re-ranked without meaning: %s", req.case_id, exc)
                        orders = None
                    dense = orders[1] if orders is not None else []
                    pairs_by_id = {pid: node.pair for pid, node in index.nodes.items()}
                    if settings.select_mode in RERANK_MODES:
                        better = fused_rank(self.ranking_orders(req.user_id, req.user_input, ordered, dense) + [([c.pair.pair_id for c in packet.records], 1.0)])
                        packet = refill(packet, better, pairs_by_id, settings.search_record_chars) if settings.select_mode == "refill" else swap_in(packet, better, pairs_by_id, settings.swap_top)
                    else:
                        extra = self.widening(req.user_id, req.user_input, dense, anchored)
                        packet = widen(packet, [Candidate(pair=pairs_by_id[pid], reasons=["widen"]) for pid in extra if pid in pairs_by_id], settings.widen_chars)
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
        # tool_calls is the self-report of calls the tool endpoint acknowledged, which the validator also observes;
        # it matches the observed trajectory. Records-lane memory reads cross that endpoint too, as in the baseline,
        # and their answers come from this harness's store; action-lane memory reads stay local and are not listed.
        return RunResponse(final_text=plain_hyphens(outcome.content) or "", tool_calls=executor.observed, prompt_tokens=tally.prompt, output_tokens=tally.output, latency_ms=latency_ms, answer=plain_hyphens(outcome.answer), abstain=False)
