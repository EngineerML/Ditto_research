"""Hades v6's own lane rules and record selection, run on lab cases with no model calls.

Imports the released source where it was unpacked (released/hades-v6_e6638d76/src, not
committed) and follows app/engine/agent.py step for step. Steps that need the model are
left out: the records-lane recall turn (its pins) and the advisory passes. What comes
out is the record set Hades puts in front of the model before any model call.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from lab.data import ROOT, Case

SRC = ROOT / "released" / "hades-v6_e6638d76" / "src"
sys.path.insert(0, str(SRC))

from app.config import Settings  # noqa: E402
from app.engine.short import find_topic, focus_token, short_records, topic_lead  # noqa: E402
from app.memory.embedding import fuse  # noqa: E402
from app.memory.packet import build_packet, identifier_focus  # noqa: E402
from app.memory.retrieval import Retriever, asked_part  # noqa: E402
from app.memory.store import Store  # noqa: E402
from app.protocol import MemoryPair, ToolDefinition  # noqa: E402
from app.routing.lane import RECORDS, Lane, about_own_records, classify, own_records_question  # noqa: E402

SETTINGS = Settings.from_env()


@dataclass
class Selection:
    pair_ids: list[str]
    chars: int
    path: str


class HadesWorld:
    """One Hades store and retriever per distinct record snapshot."""

    def __init__(self) -> None:
        self._worlds: dict[int, tuple[Store, Retriever]] = {}

    def world(self, case: Case) -> tuple[Store, Retriever]:
        key = id(case.store)
        if key not in self._worlds:
            store = Store(":memory:")
            store.upsert_seed(case.user, [MemoryPair(pair_id=r.pair_id, session_id=r.session_id, timestamp=r.timestamp,
                                                      prompt=r.prompt, response=r.response) for r in case.store], [], [])
            self._worlds[key] = (store, Retriever(store, coverage_floor=SETTINGS.coverage_floor))
        return self._worlds[key]


def catalog(case: Case) -> list[ToolDefinition]:
    return [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in case.catalog]


def route(case: Case, worlds: HadesWorld) -> Lane:
    _, retriever = worlds.world(case)
    tools = catalog(case)
    levers = SETTINGS.levers
    lane = classify(case.text, tools, levers.typo_cues, preamble=levers.route_preamble, asking=levers.route_asking,
                    anchor=levers.route_anchor, lexicon=levers.route_lexicon, operands=levers.route_operands, save=levers.route_save)
    ordered, _ = retriever.rank(case.user, case.text)
    index = retriever.index(case.user)
    focus = identifier_focus(case.text, ordered)
    if lane.name != RECORDS and lane.reason == "live" and focus:
        return Lane(RECORDS, "identifier")
    if lane.name != RECORDS and SETTINGS.short_route and focus and own_records_question(case.text, tools):
        return Lane(RECORDS, "identifier-held")
    if lane.name != RECORDS and lane.reason == "live" and about_own_records(case.text, tools, lane, index, retriever.question_anchors(index, case.text)):
        return Lane(RECORDS, "own-records")
    return lane


def select(case: Case, lane: Lane, worlds: HadesWorld, dense=None) -> Selection:
    """dense(case, query) -> pair ids by meaning, best first; None leaves meaning out."""
    s = SETTINGS
    _, retriever = worlds.world(case)
    tools = catalog(case)
    ordered, anchored = retriever.rank(case.user, case.text)
    index = retriever.index(case.user)
    focus = identifier_focus(case.text, ordered)
    pairs = [node.pair for node in index.nodes.values()]
    if lane.name == RECORDS:
        if lane.reason != "statement" and own_records_question(case.text, tools):
            if not focus and s.short_story:
                found = find_topic(case.text, pairs, s.story_min_density, s.story_max_chars)
                if found is not None and sum(len(p.prompt) + len(p.response) for p in found.notes) <= s.story_max_chars:
                    return Selection([p.pair_id for p in found.notes], sum(len(p.prompt) + len(p.response) for p in found.notes), "topic")
            if focus and s.short_programs and short_records(focus, s.short_max_chars) and focus_token(case.text, focus):
                return Selection([c.pair.pair_id for c in focus], sum(len(c.pair.prompt) + len(c.pair.response) for c in focus), "short")
        query = asked_part(case.text) if focus else case.text
        lexical = ordered if query == case.text else retriever.rank(case.user, query)[0]
        fused = fuse([c.pair.pair_id for c in lexical], dense(case, query)) if dense is not None else None
        packet = build_packet(ordered, anchored, s.packet_char_budget, s.arc_contiguous, s.thread_first, case.text,
                              closure=s.evidence_closure, index=index if s.link_hop else None, fused=fused,
                              meaning_records=s.meaning_records, meaning_chars=s.meaning_chars, ceiling=s.long_packet_chars,
                              meaning_order=s.meaning_order)
        return Selection([c.pair.pair_id for c in packet.records], packet.chars, "records")
    packet = build_packet(ordered, anchored, s.packet_char_budget, s.arc_contiguous, s.thread_first, case.text,
                          closure=s.evidence_closure, index=index if s.link_hop else None)
    if s.action_topic and not focus and own_records_question(case.text, tools):
        packet, _ = topic_lead(case.text, packet, pairs, s.story_min_density, s.story_max_chars)
    return Selection([c.pair.pair_id for c in packet.records], packet.chars, "action")


def lexical_order(case: Case, worlds: HadesWorld) -> list[str]:
    _, retriever = worlds.world(case)
    return [c.pair.pair_id for c in retriever.rank(case.user, case.text)[0]]


def full_text_hits(case: Case, worlds: HadesWorld, limit: int = 20) -> list[str]:
    store, _ = worlds.world(case)
    return [hit.pair.pair_id for hit in store.search(case.user, case.text, limit=limit)]
