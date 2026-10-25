"""Our harness's lane choice on lab cases, in variants, with no chat calls.

    .venv/bin/python -m lab.route_ours OUT.json SEED [SEED ...]

Calls the harness's own CaseRunner.choose_lane (word rules, typo mending, overrides) and then
the meaning router's vote over app/routing/intents.tsv with the same guards as
CaseRunner.meaning_lane, so what is measured is what ships. Each variant switches the new
pieces through the settings: typo mending, the own-records override with the product
question rule, the guards on meaning flips, and the meaning threshold. Runs in its own
process because the harness, Hades and dan0l each ship a package named `app`. Embeddings come
from the lab's cache (one per question and bank example).
"""
from __future__ import annotations

import dataclasses
import json
import sys
from types import SimpleNamespace

import numpy as np

from lab import data
from lab.embed import Embedder

sys.path.insert(0, str(data.ROOT / "harness"))

from app.config import Settings  # noqa: E402
from app.engine.agent import IDENTIFIER_REASONS, CaseRunner  # noqa: E402
from app.memory.packet import identifier_focus  # noqa: E402
from app.memory.retrieval import Retriever  # noqa: E402
from app.memory.store import Store  # noqa: E402
from app.protocol import MemoryPair, RunRequest, ToolDefinition  # noqa: E402
from app.routing import lane as L  # noqa: E402
from app.routing.meaning import NEAREST, read_bank  # noqa: E402

BASE = Settings.from_env()
OFF = dict(route_mend=False, route_own=False, meaning_guards=False)
VARIANTS = {
    "v1": (OFF, 0.8),
    "mend": ({**OFF, "route_mend": True}, 0.8),
    "own": ({**OFF, "route_own": True}, 0.8),
    "guards": ({**OFF, "meaning_guards": True}, 0.8),
    "all@0.80": ({}, 0.8),
    "all@0.85": ({}, 0.85),
    "all@0.90": ({}, 0.9),
    "rules-new": ({}, 2.0),
}


def settings_for(levers: dict, sure: float) -> Settings:
    return dataclasses.replace(BASE, levers=dataclasses.replace(BASE.levers, **levers), meaning_sure=sure)


class World:
    def __init__(self) -> None:
        self._worlds: dict[int, Retriever] = {}

    def retriever(self, case: data.Case) -> Retriever:
        key = id(case.store)
        if key not in self._worlds:
            store = Store(":memory:")
            store.upsert_seed(case.user, [MemoryPair(pair_id=r.pair_id, session_id=r.session_id, timestamp=r.timestamp,
                                                      prompt=r.prompt, response=r.response) for r in case.store], [], [])
            self._worlds[key] = Retriever(store, coverage_floor=BASE.coverage_floor)
        return self._worlds[key]


class Bank:
    def __init__(self, embedder: Embedder) -> None:
        rows = read_bank()
        self.matrix = embedder.vectors([text for _, text in rows])
        self.labels = np.array([1.0 if lane == L.RECORDS else 0.0 for lane, _ in rows])

    def sense(self, vector: np.ndarray) -> tuple[str, float]:
        scores = self.matrix @ vector
        top = np.argsort(-scores)[:NEAREST]
        weights = np.maximum(scores[top], 0.0) + 1e-6
        share = float((weights * self.labels[top]).sum() / weights.sum())
        return (L.RECORDS, share) if share >= 0.5 else (L.ACTION, 1.0 - share)


def route(case: data.Case, world: World, sense: tuple[str, float], settings: Settings) -> str:
    retriever = world.retriever(case)
    tools = [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in case.catalog]
    req = RunRequest(case_id=case.key, user_input=case.text, tools=tools, user_id=case.user)
    ordered, _ = retriever.rank(case.user, case.text)
    index = retriever.index(case.user)
    focus = identifier_focus(case.text, ordered)
    lane, routed = CaseRunner.choose_lane(SimpleNamespace(settings=settings, retriever=retriever), req, ordered, index, focus)
    side, share = sense
    if lane.reason in IDENTIFIER_REASONS or share < settings.meaning_sure or side == lane.name:
        return f"{lane.name}:{lane.reason}"
    guards = settings.levers.meaning_guards
    if side == L.RECORDS:
        if guards and L.keeps_action(routed):
            return f"{lane.name}:{lane.reason}"
        return "records:statement" if L.tells_without_asking(routed) else "records:meaning"
    if guards and L.keeps_records(routed, tools):
        return f"{lane.name}:{lane.reason}"
    return "action:meaning"


def main() -> None:
    out, seeds = sys.argv[1], [int(s) for s in sys.argv[2:]]
    embedder = Embedder(0.05)
    bank = Bank(embedder)
    world = World()
    variants = {name: settings_for(levers, sure) for name, (levers, sure) in VARIANTS.items()}
    picks: dict[str, dict[str, str]] = {name: {} for name in variants}
    for seed in seeds:
        cases = data.load(seed)
        vectors = embedder.vectors([c.text for c in cases])
        for case, vector in zip(cases, vectors):
            sense = bank.sense(vector)
            for name, settings in variants.items():
                picks[name][case.key] = route(case, world, sense, settings)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(picks, fh)
    print(f"our routes, {len(variants)} variants x {sum(len(v) for v in picks.values()) // len(variants)} cases -> {out}")


if __name__ == "__main__":
    main()
