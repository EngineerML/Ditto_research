"""Record selection at a fixed size: re-rank instead of adding.

    bash lab/run.sh lab.eval_rank --seeds 201,202 --salt 5

For every case this computes, once: Hades's own packet (as released, with meaning), Hades's
lexical order, the meaning order, and the full-text (bm25) order. Variants then pick records
under a character budget, and every number is reported next to Hades at the same size:

- hades:        the released packet
- rrf@hades:    reciprocal-rank fusion of the orders, filled to Hades's own packet size
- swap@hades:   Hades's packet, with its weakest records swapped for better-fused ones, same size
- rrf@N:        fusion filled to a fixed number of characters (action lane: smaller packets)

Costs only embeddings (cached), no chat calls.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from lab import data, designs, hades
from lab.embed import Embedder
from lab.meaning import Meaning

RESULTS = Path(__file__).resolve().parent / "results"
RRF_K = 60


@dataclass
class Prepared:
    case: data.Case
    lane: str
    hades_ids: list[str]
    hades_path: str
    lexical: list[str]
    dense: list[str]
    fulltext: list[str]
    sizes: dict[str, int]
    texts: dict[str, str]


def fuse(orders: list[tuple[list[str], float]], depth: int = 80) -> list[str]:
    score: dict[str, float] = collections.defaultdict(float)
    for order, weight in orders:
        for rank, pid in enumerate(order[:depth], start=1):
            score[pid] += weight / (RRF_K + rank)
    return sorted(score, key=lambda pid: -score[pid])


def fill(order: list[str], sizes: dict[str, int], budget: int, keep: list[str] = ()) -> list[str]:
    kept, used = list(keep), sum(sizes[p] for p in keep)
    for pid in order:
        if pid in kept:
            continue
        if used + sizes[pid] > budget:
            continue
        kept.append(pid)
        used += sizes[pid]
    return kept


def swap(base: list[str], better: list[str], sizes: dict[str, int], budget: int, top: int) -> list[str]:
    """Bring the best `top` fused records into `base`, dropping base records that rank lowest in the fusion."""
    rank = {pid: i for i, pid in enumerate(better)}
    kept = list(base)
    for pid in better[:top]:
        if pid in kept:
            continue
        used = sum(sizes[p] for p in kept)
        victims = sorted((p for p in kept if p not in better[:top]), key=lambda p: -rank.get(p, 10**6))
        while used + sizes[pid] > budget and victims:
            out = victims.pop(0)
            kept.remove(out)
            used -= sizes[out]
        if used + sizes[pid] <= budget:
            kept.append(pid)
    return kept


def prepare(case: data.Case, worlds: hades.HadesWorld, meaning: Meaning) -> Prepared:
    lane = case.lane if case.lane != "none" else designs.ACTION
    pick = designs.pick_hades(case, lane, worlds, meaning)
    sizes = {r.pair_id: len(r.text) for r in case.store}
    return Prepared(case, lane, pick.pair_ids, pick.path, hades.lexical_order(case, worlds), meaning.order(case),
                    hades.full_text_hits(case, worlds, 40), sizes, {r.pair_id: r.text.lower() for r in case.store})


def variants(p: Prepared) -> dict[str, list[str]]:
    size_h = sum(p.sizes[i] for i in p.hades_ids)
    out = {"hades": p.hades_ids}
    if p.hades_path in ("short", "topic"):
        return out | {k: p.hades_ids for k in ("rrf@hades", "swap@hades", "swap8@hades", "rrf@6k", "rrf@12k", "rrf@hades/2")}
    lexical_dense = [(p.lexical, 1.0), (p.dense, 1.0), (p.fulltext, 0.5), (p.hades_ids, 1.0)]
    fused = fuse(lexical_dense)
    out["rrf@hades"] = fill(fused, p.sizes, size_h)
    out["swap@hades"] = swap(p.hades_ids, fused, p.sizes, size_h, top=12)
    out["swap8@hades"] = swap(p.hades_ids, fused, p.sizes, size_h, top=8)
    out["rrf@hades/2"] = fill(fused, p.sizes, size_h // 2)
    out["rrf@6k"] = fill(fused, p.sizes, 6000)
    out["rrf@12k"] = fill(fused, p.sizes, 12000)
    return out


def score(p: Prepared, ids: list[str]) -> dict:
    sel = set(ids)
    found = len(p.case.needs & sel)
    text = " ".join(p.texts[i] for i in ids)
    answers = [a.lower() for a in p.case.answers if a]
    store_text = " ".join(p.texts.values())
    eligible = bool(answers) and all(a in store_text for a in answers)
    return {"complete": p.case.needs <= sel, "recall": found / len(p.case.needs), "precision": found / max(1, len(sel)),
            "tokens": sum(p.sizes[i] for i in ids) / 4, "answer_eligible": eligible,
            "answer_seen": eligible and all(a in text for a in answers)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], default=[201, 202])
    ap.add_argument("--salt", type=int, default=5)
    args = ap.parse_args()
    embedder = Embedder(0.05)
    meaning = Meaning(embedder)
    rows: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    misses: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for seed in args.seeds:
        cases = data.load(seed, args.salt)
        worlds = hades.HadesWorld()
        meaning.queries([c.text for c in cases])
        for case in cases:
            if not case.needs:
                continue
            p = prepare(case, worlds, meaning)
            for name, ids in variants(p).items():
                s = score(p, ids)
                rows[(name, p.lane)].append(s)
                if not s["complete"]:
                    misses[f"{name}|{p.lane}"][case.kind] += 1
        print(f"seed {seed} salt {args.salt} done, embeddings ${embedder.spent:.4f}", flush=True)
    print(f"\n{'variant':14s} {'lane':8s} {'cases':>5s} {'complete':>8s} {'recall':>7s} {'precis':>7s} {'answer':>7s} {'tok med':>8s} {'tok mean':>8s} {'tok p90':>8s}")
    summary = {}
    for (name, lane), rs in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        m = lambda k: statistics.fmean(float(r[k]) for r in rs)
        elig = [r for r in rs if r["answer_eligible"]]
        toks = sorted(r["tokens"] for r in rs)
        summary[f"{name}|{lane}"] = {"cases": len(rs), "complete": m("complete"), "recall": m("recall"), "precision": m("precision"),
                                     "answer_seen": statistics.fmean(float(r["answer_seen"]) for r in elig) if elig else None,
                                     "tokens_median": toks[len(toks) // 2], "tokens_mean": m("tokens"), "tokens_p90": toks[int(len(toks) * 0.9)]}
        s = summary[f"{name}|{lane}"]
        print(f"{name:14s} {lane:8s} {s['cases']:5d} {s['complete']:8.3f} {s['recall']:7.3f} {s['precision']:7.3f} "
              f"{(s['answer_seen'] or 0):7.3f} {s['tokens_median']:8.0f} {s['tokens_mean']:8.0f} {s['tokens_p90']:8.0f}")
    print("\nkinds left incomplete (top 4 per variant):")
    for key in sorted(misses):
        print(f"  {key:24s} {misses[key].most_common(4)}")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"rank_seeds{'-'.join(map(str, args.seeds))}_salt{args.salt}.json"
    out.write_text(json.dumps(summary, indent=1))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
