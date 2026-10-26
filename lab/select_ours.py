"""The records our harness puts in front of its deciding model, on lab cases, with no chat calls.

    .venv/bin/python -m lab.select_ours OUT.json SEED [SEED ...]

Routes with the shipped settings (lab.route_ours, variant all@0.85), then follows
app/engine/agent.py: the topic path's records (with the contact cards of the people they name,
its fallback when the thread reading is left out), the program path's records, or the
records lane's packet refilled from the fused lexical, meaning and full-text orders, or the
action lane's packet with the topic records, refilled the same way. Left out: the recall
turn's pins (they need the model). Embeddings come from the lab cache.
"""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from lab import data
from lab.embed import Embedder
from lab.meaning import Meaning
from lab.route_ours import VARIANTS, Bank, World, route, settings_for

from app.engine.agent import SWAP_TEXT_HITS, CaseRunner  # noqa: E402
from app.engine.short import CONTACT_RE, find_topic, focus_token, record_size, short_records, topic_lead  # noqa: E402
from app.memory.embedding import fuse  # noqa: E402
from app.memory.packet import build_packet, fused_rank, identifier_focus, refill  # noqa: E402
from app.memory.people import cards_for, full_names  # noqa: E402
from app.memory.retrieval import asked_part  # noqa: E402
from app.routing.lane import asks_stored_detail, own_records_question  # noqa: E402
from app.protocol import RunRequest, ToolDefinition  # noqa: E402

SETTINGS = settings_for(*VARIANTS["all@0.85"])


def with_cards(notes, pairs):
    named = full_names("\n".join(p.prompt + "\n" + p.response for p in notes), pairs)
    out, held = list(notes), {p.pair_id for p in notes}
    for pair in cards_for(named, pairs):
        if pair.pair_id not in held and sum(record_size(p) for p in out + [pair]) <= SETTINGS.story_max_chars:
            out.append(pair)
            held.add(pair.pair_id)
    return out


def refilled(case, retriever, packet, ordered, dense, pairs_by_id):
    hits = [hit.pair.pair_id for hit in retriever.store.search(case.user, case.text, limit=SWAP_TEXT_HITS)]
    orders = [([c.pair.pair_id for c in ordered], 1.0), (dense, 1.0), (hits, 0.5)]
    better = fused_rank(orders + [([c.pair.pair_id for c in packet.records], 1.0)])
    return refill(packet, better, pairs_by_id, SETTINGS.search_record_chars)


def select(case: data.Case, world: World, meaning: Meaning, sense) -> dict:
    s = SETTINGS
    pick = route(case, world, sense, s)
    lane, reason = pick.split(":", 1)
    retriever = world.retriever(case)
    index = retriever.index(case.user)
    pairs = [node.pair for node in index.nodes.values()]
    pairs_by_id = {node.pair.pair_id: node.pair for node in index.nodes.values()}
    tools = [ToolDefinition(name=t["name"], description=t.get("description", "")) for t in case.catalog]
    text = case.text
    ordered, anchored = retriever.rank(case.user, text)
    focus = identifier_focus(text, ordered)
    path, ids = "", []
    if lane == "records":
        if reason != "statement" and own_records_question(text, tools):
            if not focus and s.short_story:
                found = find_topic(text, pairs, s.story_min_density, s.story_max_chars)
                if found is not None and sum(record_size(p) for p in found.notes) <= s.story_max_chars:
                    notes = with_cards(found.notes, pairs) if CONTACT_RE.search(text) else found.notes
                    path, ids = "topic", [p.pair_id for p in notes]
            elif focus and s.short_programs and short_records(focus, s.short_max_chars) and focus_token(text, focus):
                path, ids = "program", [c.pair.pair_id for c in focus]
        if not path and s.levers.stored_topic and not focus and reason != "statement":
            req = RunRequest(case_id=case.key, user_input=text, tools=tools, user_id=case.user)
            _, routed = CaseRunner.choose_lane(SimpleNamespace(settings=s, retriever=retriever), req, ordered, index, focus)
            if asks_stored_detail(routed):
                found = find_topic(text, pairs, s.story_min_density, s.story_max_chars)
                if found is not None and sum(record_size(p) for p in found.notes) <= s.story_max_chars:
                    notes = with_cards(found.notes, pairs) if CONTACT_RE.search(text) else found.notes
                    path, ids = "stored-topic", [p.pair_id for p in notes]
        if not path:
            query = asked_part(text) if focus else text
            lexical = ordered if query == text else retriever.rank(case.user, query)[0]
            dense = meaning.order(case, query)
            fused = fuse([c.pair.pair_id for c in lexical], dense)
            packet = build_packet(ordered, anchored, s.packet_char_budget, s.arc_contiguous, s.thread_first, text, closure=s.evidence_closure,
                                  index=index if s.link_hop else None, fused=fused, meaning_records=s.meaning_records, meaning_chars=s.meaning_chars,
                                  ceiling=s.long_packet_chars, meaning_order=s.meaning_order)
            packet = refilled(case, retriever, packet, ordered, dense, pairs_by_id)
            path, ids = "records", [c.pair.pair_id for c in packet.records]
    else:
        packet = build_packet(ordered, anchored, s.packet_char_budget, s.arc_contiguous, s.thread_first, text, closure=s.evidence_closure,
                              index=index if s.link_hop else None)
        path = "action"
        if s.action_topic and not focus and own_records_question(text, tools):
            packet, lead = topic_lead(text, packet, pairs, s.story_min_density, s.story_max_chars)
            path = "action+topic" if lead else path
        if packet.records:
            packet = refilled(case, retriever, packet, ordered, meaning.order(case, text), pairs_by_id)
        ids = [c.pair.pair_id for c in packet.records]
    sizes = {p.pair_id: len(p.prompt) + len(p.response) for p in pairs}
    return {"lane": lane, "path": path, "ids": ids, "chars": sum(sizes.get(i, 0) for i in ids)}


def main() -> None:
    out, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]]
    embedder = Embedder(0.20)
    meaning, bank, world = Meaning(embedder), Bank(embedder), World()
    picks = {}
    for seed in seeds:
        cases = data.load(seed)
        vectors = embedder.vectors([c.text for c in cases])
        for case, vector in zip(cases, vectors):
            picks[case.key] = select(case, world, meaning, bank.sense(vector))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(picks, fh)
    print(f"our selections for {len(picks)} cases -> {out}")


if __name__ == "__main__":
    main()
