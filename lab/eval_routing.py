"""Routing only: Hades rules vs the harness's generic intent bank (kNN), and the mix.

    bash lab/run.sh lab.eval_routing --test 101,102,103 --test-salt 7

The bank is read from harness/app/routing/intents.tsv, the file that ships, so this
measures exactly what the harness routes with. Costs a few embeddings, no chat calls.
"""
from __future__ import annotations

import argparse
import collections

import numpy as np

from lab import data, designs, hades
from lab.embed import Embedder
from lab.meaning import Meaning

BANK = data.ROOT / "harness" / "app" / "routing" / "intents.tsv"


def bank() -> list[tuple[str, str]]:
    rows = []
    for line in BANK.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            lane, text = line.split("\t", 1)
            rows.append((lane.strip(), text.strip()))
    return rows


class BankRouter:
    def __init__(self, meaning: Meaning, rows: list[tuple[str, str]], k: int) -> None:
        self.meaning, self.k = meaning, k
        meaning.queries([t for _, t in rows])
        self.matrix = np.stack([meaning.query(t) for _, t in rows])
        self.labels = np.array([1.0 if lane == "records" else 0.0 for lane, _ in rows])

    def __call__(self, text: str) -> tuple[str, float]:
        scores = self.matrix @ self.meaning.query(text)
        top = np.argsort(-scores)[: self.k]
        weights = np.maximum(scores[top], 0.0) + 1e-6
        share = float((weights * self.labels[top]).sum() / weights.sum())
        return ("records", share) if share >= 0.5 else ("action", 1.0 - share)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--test", type=lambda s: [int(x) for x in s.split(",")], default=[101, 102, 103])
    ap.add_argument("--test-salt", type=int, default=7)
    ap.add_argument("--show", type=int, default=0, help="print this many misrouted questions per router")
    args = ap.parse_args()
    embedder = Embedder(0.02)
    meaning = Meaning(embedder)
    rows = bank()
    routers = {f"bank k={k}": BankRouter(meaning, rows, k) for k in (5, 9, 15)}
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    misses: dict[str, list[str]] = collections.defaultdict(list)
    for seed in args.test:
        cases = data.load(seed, args.test_salt)
        worlds = hades.HadesWorld()
        meaning.queries([c.text for c in cases])
        for case in cases:
            rules = designs.route_hades(case, worlds)[0]
            picks = {"hades": rules}
            for name, router in routers.items():
                lane, sure = router(case.text)
                picks[name] = lane
                for cut in (0.7, 0.8, 0.9):
                    picks[f"mix {name} >= {cut}"] = lane if sure >= cut else rules
            truth = "action" if case.lane == "none" else case.lane
            for name, lane in picks.items():
                counts[name][(case.lane, lane)] += 1
                if case.lane != "none" and lane != truth:
                    misses[name].append(f"{case.phase}:{case.kind} | {case.text[:110]}")
    print(f"bank: {len(rows)} examples ({sum(1 for l, _ in rows if l == 'records')} records)")
    for name, c in counts.items():
        judged = sum(v for (t, _), v in c.items() if t != "none")
        right = sum(v for (t, l), v in c.items() if t != "none" and t == l)
        rec = (c[("records", "records")], sum(v for (t, _), v in c.items() if t == "records"))
        act = (c[("action", "action")], sum(v for (t, _), v in c.items() if t == "action"))
        print(f"{name:26s} right {right / judged:.3f}  records kept {rec[0]}/{rec[1]}  action kept {act[0]}/{act[1]}")
        kinds = collections.Counter(m.split(" | ")[0] for m in misses[name])
        print(f"{'':26s} misses: {kinds.most_common(5)}")
        for m in misses[name][: args.show]:
            print(f"{'':28s}- {m}")
    print(f"embeddings ${embedder.spent:.5f}")


if __name__ == "__main__":
    main()
