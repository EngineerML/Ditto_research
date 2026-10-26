"""The records dan0l v24 puts in front of its deciding model, on lab cases, with no chat calls.

    .venv/bin/python -m lab.select_dan0l OUT.json SEED [SEED ...]

Follows app/agent.py after routing (lab.route_dan0l): the program path's records, the topic
path's records (with the contact cards of every person they name in full, its fallback when
the thread reading is left out), the records lane's packet with the meaning additions and
order, or the action lane's packet with the topic records. Left out, as for Hades in
lab/hades.py: the recall turn's pins (they need the model). Embeddings come from the lab cache.
"""
from __future__ import annotations

import json
import sys

from lab import data
from lab.embed import Embedder
from lab.meaning import Meaning
from lab.route_dan0l import SETTINGS, World, route

from app.memory.embedding import fuse  # noqa: E402
from app.memory.people import cards_for, full_names  # noqa: E402
from app.memory.retrieval import asked_part  # noqa: E402
from app.packet import build_packet, identifier_focus  # noqa: E402
from app.protocol import ToolDefinition  # noqa: E402
from app.short import CONTACT_RE, find_topic, record_size, topic_lead  # noqa: E402


def with_cards(notes, pairs):
    named = full_names("\n".join(p.prompt + "\n" + p.response for p in notes), pairs)
    out, held = list(notes), {p.pair_id for p in notes}
    for pair in cards_for(named, pairs):
        if pair.pair_id not in held and sum(record_size(p) for p in out + [pair]) <= SETTINGS.story_max_chars:
            out.append(pair)
            held.add(pair.pair_id)
    return out


def select(case: data.Case, world: World, meaning: Meaning) -> dict:
    s = SETTINGS
    picked = route(case, world)
    retriever = world.retriever(case)
    index = retriever.index(case.user)
    pairs = [node.pair for node in index.nodes.values()]
    text = case.text
    ordered, anchored = retriever.rank(case.user, text)
    focus = identifier_focus(text, ordered)
    path = picked["path"]
    if path == "program":
        ids = [c.pair.pair_id for c in focus]
    elif path in ("topic", "stored-topic"):
        notes = find_topic(text, pairs, s.story_min_density, s.story_max_chars).notes
        if CONTACT_RE.search(text):
            notes = with_cards(notes, pairs)
        ids = [p.pair_id for p in notes]
    elif path == "records":
        query = asked_part(text) if focus else text
        lexical = ordered if query == text else retriever.rank(case.user, query)[0]
        fused = fuse([c.pair.pair_id for c in lexical], meaning.order(case, query))
        packet = build_packet(ordered, anchored, s.packet_char_budget, text, index, fused, s.meaning_records, s.meaning_chars, s.long_packet_chars)
        ids = [c.pair.pair_id for c in packet.records]
    else:
        packet = build_packet(ordered, anchored, s.packet_char_budget, text, index)
        if path == "action+topic":
            packet, _ = topic_lead(text, packet, pairs, s.story_min_density, s.story_max_chars)
        ids = [c.pair.pair_id for c in packet.records]
    sizes = {p.pair_id: len(p.prompt) + len(p.response) for p in pairs}
    return {"lane": picked["lane"], "path": path, "ids": ids, "chars": sum(sizes.get(i, 0) for i in ids)}


def main() -> None:
    out, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]]
    world, meaning = World(), Meaning(Embedder(0.20))
    picks = {}
    for seed in seeds:
        for case in data.load(seed):
            picks[case.key] = select(case, world, meaning)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(picks, fh)
    print(f"dan0l v24 selections for {len(picks)} cases -> {out}")


if __name__ == "__main__":
    main()
