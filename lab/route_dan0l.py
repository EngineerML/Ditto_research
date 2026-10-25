"""dan0l v24's lane and path choice on lab cases, with no model calls.

    .venv/bin/python -m lab.route_dan0l OUT.json SEED [SEED ...]

Imports the released source (released/dan0l-v24_ecf5a1a2/src, not committed) and follows
app/agent.py step for step: the word rules on the main clause, the overrides after
ranking, then which records-lane path would take the request (program, topic, the
stored-detail topic path, or the full records lane). Runs in its own process because
dan0l and Hades both ship a package named `app`.
"""
from __future__ import annotations

import json
import sys

from lab import data

SRC = data.ROOT / "released" / "dan0l-v24_ecf5a1a2" / "src"
sys.path.insert(0, str(SRC))

from app.config import Settings  # noqa: E402
from app.lane import RECORDS, Lane, about_own_records, classify, main_clause, names_held_alias, own_records_question  # noqa: E402
from app.memory.retrieval import Retriever  # noqa: E402
from app.packet import held_identifier, identifier_focus  # noqa: E402
from app.protocol import MemoryPair, ToolDefinition  # noqa: E402
from app.short import find_topic, focus_token, nicknames, short_records  # noqa: E402
from app.store import Store  # noqa: E402

SETTINGS = Settings.from_env()


class World:
    def __init__(self) -> None:
        self._worlds: dict[int, Retriever] = {}

    def retriever(self, case: data.Case) -> Retriever:
        key = id(case.store)
        if key not in self._worlds:
            store = Store(":memory:")
            store.upsert_seed(case.user, [MemoryPair(pair_id=r.pair_id, session_id=r.session_id, timestamp=r.timestamp,
                                                      prompt=r.prompt, response=r.response) for r in case.store], [], [])
            self._worlds[key] = Retriever(store, coverage_floor=SETTINGS.coverage_floor)
        return self._worlds[key]


def route(case: data.Case, world: World) -> dict[str, str]:
    s = SETTINGS
    tools = [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in case.catalog]
    retriever = world.retriever(case)
    text = case.text
    lane = classify(main_clause(text), tools)
    first = lane
    ordered, _ = retriever.rank(case.user, text)
    index = retriever.index(case.user)
    focus = identifier_focus(text, ordered)
    if lane.name != RECORDS and lane.reason == "live" and focus:
        lane = Lane(RECORDS, "identifier")
    elif lane.name != RECORDS and focus and own_records_question(text, tools, carried=True):
        lane = Lane(RECORDS, "identifier-held")
    elif lane.name != RECORDS and lane.reason == "live" and about_own_records(text, tools, lane, index, retriever.question_anchors(index, text)):
        lane = Lane(RECORDS, "own-records")
    elif lane.name != RECORDS and lane.reason == "default" and own_records_question(text, tools, working=True) and held_identifier(text, ordered):
        lane = Lane(RECORDS, "identifier-read")
    pairs = [node.pair for node in index.nodes.values()]
    path = "action"
    if lane.name == RECORDS:
        path = "records"
        if lane.reason != "statement" and own_records_question(text, tools, carried=bool(focus)):
            if not focus:
                if find_topic(text, pairs, s.story_min_density, s.story_max_chars) is not None:
                    path = "topic"
            elif short_records(focus, s.short_max_chars) and focus_token(text, focus):
                path = "program"
        if path == "records" and not focus and lane.reason == "stored-detail" and not own_records_question(text, tools):
            if find_topic(text, pairs, s.story_min_density, s.story_max_chars) is not None:
                path = "stored-topic"
    elif not focus and (own_records_question(text, tools) or names_held_alias(text, tools, index, nicknames(pairs))):
        if find_topic(text, pairs, s.story_min_density, s.story_max_chars) is not None:
            path = "action+topic"
    return {"lane": lane.name, "reason": lane.reason, "rules": f"{first.name}:{first.reason}", "path": path}


def main() -> None:
    out, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]]
    world = World()
    picks: dict[str, dict[str, str]] = {}
    for seed in seeds:
        for case in data.load(seed):
            picks[case.key] = route(case, world)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(picks, fh)
    print(f"dan0l v24 routes for {len(picks)} cases -> {out}")


if __name__ == "__main__":
    main()
