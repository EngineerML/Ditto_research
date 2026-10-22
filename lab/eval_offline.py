"""Compare routing and record selection designs offline, with no chat-model calls.

    bash lab/run.sh lab.eval_offline --train 11,12,13,14 --test 101,102,103 --test-salt 7

Routing truth: memory questions and tool questions whose expected tools are memory
reads belong in the records lane; every other tool question in the action lane. Tool
questions that expect no call at all ("none") are reported apart: whether they pass
depends on the model reading the records, not on the lane.

Selection truth: a case's needed records (memory: the answer key's evidence ids; tool:
small prerequisite sets and the records holding a required argument). "complete" =
every needed record selected. "answer seen" = every answer value is in the selected
text, counted only where the value is written in the records at all.

Only embeddings are paid for (about $0.001 per dataset). Results go to lab/results/.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from lab import data, designs, hades
from lab.embed import Embedder
from lab.meaning import Meaning

RESULTS = Path(__file__).resolve().parent / "results"
TOKENS_PER_CHAR = 0.25


def ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()]


class Tally:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = collections.defaultdict(list)

    def add(self, design: str, case: data.Case, pick: designs.Pick, store_text: str) -> None:
        selected = set(pick.pair_ids)
        found = len(case.needs & selected)
        answers = [a.lower() for a in case.answers if a]
        eligible = bool(answers) and all(a in store_text for a in answers)
        self.rows[design].append({
            "lane": case.lane, "kind": case.kind, "has_needs": bool(case.needs),
            "complete": bool(case.needs) and case.needs <= selected,
            "recall": found / len(case.needs) if case.needs else None,
            "precision": found / len(selected) if case.needs and selected else None,
            "tokens": pick.chars * TOKENS_PER_CHAR,
            "answer_eligible": eligible,
            "answer_seen": eligible and all(a in pick.text.lower() for a in answers),
        })

    def summary(self) -> dict[str, dict[str, dict]]:
        out: dict[str, dict[str, dict]] = {}
        for design, rows in self.rows.items():
            out[design] = {}
            for lane in ("records", "action", "all"):
                part = [r for r in rows if lane == "all" or r["lane"] == lane]
                needed = [r for r in part if r["has_needs"]]
                eligible = [r for r in part if r["answer_eligible"]]
                tokens = sorted(r["tokens"] for r in part) or [0]
                out[design][lane] = {
                    "cases": len(part),
                    "complete": mean(r["complete"] for r in needed),
                    "recall": mean(r["recall"] for r in needed),
                    "precision": mean(r["precision"] for r in needed),
                    "answer_seen": mean(r["answer_seen"] for r in eligible),
                    "tokens_median": tokens[len(tokens) // 2],
                    "tokens_p90": tokens[int(len(tokens) * 0.9)],
                }
        return out


def mean(values) -> float | None:
    values = [float(v) for v in values if v is not None]
    return round(statistics.fmean(values), 4) if values else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--train", type=ints, default=ints("11,12,13,14"))
    ap.add_argument("--train-salts", type=ints, default=ints("0,3"))
    ap.add_argument("--test", type=ints, default=ints("101,102,103"))
    ap.add_argument("--test-salt", type=int, default=7)
    ap.add_argument("--budget-usd", type=float, default=0.05)
    ap.add_argument("--no-meaning", action="store_true", help="skip every design that needs embeddings")
    ap.add_argument("--only", default="", help="comma list of selector names to run (default: all)")
    ap.add_argument("--no-knn", action="store_true", help="skip the benchmark-trained kNN routers")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    wanted = lambda name: not only or name in only

    started = time.time()
    embedder = Embedder(args.budget_usd)
    meaning = None if args.no_meaning else Meaning(embedder)
    knn = None
    if meaning is not None and not args.no_knn:
        train = [c for seed in args.train for salt in args.train_salts for c in data.load(seed, salt)]
        knn = designs.KNNRouter(meaning, train)
        print(f"train cases {len(train)} from seeds {args.train} salts {args.train_salts}", flush=True)

    routing: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    misrouted: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    tally = Tally()
    for seed in args.test:
        cases = data.load(seed, args.test_salt)
        worlds = hades.HadesWorld()
        if meaning is not None:
            meaning.queries([c.text for c in cases])
        store_texts: dict[int, str] = {}
        for case in cases:
            key = id(case.store)
            if key not in store_texts:
                store_texts[key] = "\n".join(r.text for r in case.store).lower()
            routes = {"hades": designs.route_hades(case, worlds)[0]}
            if knn is not None:
                routes |= {"knn": knn(case)[0],
                           "combo80": designs.route_combo(case, worlds, knn, 0.80)[0],
                           "combo90": designs.route_combo(case, worlds, knn, 0.90)[0]}
            for name, lane in routes.items():
                truth = case.lane if case.lane != "none" else "none"
                routing[name][(truth, lane)] += 1
                if truth != "none" and lane != truth:
                    misrouted[name][f"{case.phase}:{case.kind}"] += 1
            lane = case.lane if case.lane != "none" else designs.ACTION
            text = store_texts[key]
            picks = {
                "hades (no meaning)": lambda: designs.pick_hades(case, lane, worlds, None),
                "full-text k=16": lambda: designs.whole(case, hades.full_text_hits(case, worlds, 16)),
            }
            if meaning is not None:
                picks |= {
                    "hades": lambda: designs.pick_hades(case, lane, worlds, meaning),
                    **{f"dense k={k}": (lambda k=k: designs.pick_dense(case, meaning, k)) for k in (8, 16, 32)},
                    "overhorizon": lambda: designs.pick_overhorizon(case, lane, meaning, worlds),
                    "union": lambda: designs.pick_union(case, lane, worlds, meaning),
                    "harness union": lambda: designs.pick_union(case, lane, worlds, meaning, budget=40000, keep_short_paths=True),
                }
            for name, make in picks.items():
                if wanted(name):
                    tally.add(name, case, make(), text)
        print(f"seed {seed} salt {args.test_salt} done, {time.time() - started:.0f}s, embeddings ${embedder.spent:.4f}", flush=True)

    print("\n== routing (truth -> chosen), test seeds", args.test, "salt", args.test_salt)
    route_rows = {}
    for name, counts in routing.items():
        judged = {k: v for k, v in counts.items() if k[0] != "none"}
        right = sum(v for k, v in judged.items() if k[0] == k[1])
        rec_total = sum(v for k, v in judged.items() if k[0] == "records")
        act_total = sum(v for k, v in judged.items() if k[0] == "action")
        rec_ok = counts[("records", "records")]
        act_ok = counts[("action", "action")]
        none_split = {lane: counts[("none", lane)] for lane in ("records", "action")}
        route_rows[name] = {"accuracy": right / sum(judged.values()), "records_ok": f"{rec_ok}/{rec_total}",
                            "action_ok": f"{act_ok}/{act_total}", "none_cases": none_split,
                            "top_misses": misrouted[name].most_common(6)}
        print(f"{name:9s} accuracy {right / sum(judged.values()):.3f}  records kept {rec_ok}/{rec_total}  "
              f"action kept {act_ok}/{act_total}  no-call cases sent to {none_split}")
        print(f"          most misrouted: {misrouted[name].most_common(6)}")

    summary = tally.summary()
    print("\n== selection with the true lane")
    print(f"{'design':20s} {'lane':8s} {'complete':>8s} {'recall':>7s} {'precis':>7s} {'answer':>7s} {'tok med':>8s} {'tok p90':>8s}")
    for design, lanes in summary.items():
        for lane, s in lanes.items():
            if lane == "all":
                continue
            fmt = lambda v: "-" if v is None else f"{v:.3f}"
            print(f"{design:20s} {lane:8s} {fmt(s['complete']):>8s} {fmt(s['recall']):>7s} {fmt(s['precision']):>7s} "
                  f"{fmt(s['answer_seen']):>7s} {s['tokens_median']:>8.0f} {s['tokens_p90']:>8.0f}")

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"{stamp}_offline_salt{args.test_salt}.json"
    out.write_text(json.dumps({"args": vars(args), "routing": route_rows, "selection": summary,
                               "embedding_usd": round(embedder.spent, 5)}, indent=1, default=str))
    print(f"\nsaved {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}; embeddings ${embedder.spent:.4f}")


if __name__ == "__main__":
    main()
