#!/usr/bin/env python3
"""Points lost per run, by family, for our code against the top agents (public bench-15 case results).

    python3 v15_atlas/family_gaps.py LIVE_DIR OUT.md

Our code: horizon v8's live scoring runs plus the local paid seed-5119 run of the same build; on the memory side also
DrPresident v23's bench-15 runs (v8's memory path is v23's, byte for byte). A family is a real gap when our loss is at
least 0.3 a run over every run we have and the best other agent loses at most a third of that over 3+ runs.
"""
import glob
import json
import os
import sys
from collections import defaultdict

LIVE, OUT = sys.argv[1], sys.argv[2]
ROOT = "/home/bittensor/ditto"


def runs_of(path):
    p = json.load(open(path))
    return [r["case_results"] for r in (p.get("provisional_scores") or []) if r.get("bench_version") == 15 and r.get("case_results")]


agents = {os.path.basename(f)[:-5]: runs_of(f) for f in glob.glob(f"{LIVE}/*.json")}
ours_tool = agents.pop("horizon_v8") + [json.load(open(f"{ROOT}/practice/20261103T003809Z_ditto-harness-drp23v15_full/report.json"))["report"]["per_case"]]
dp23 = runs_of(f"{ROOT}/live/2026-11-03/compare/DrPresident_v23.json")
ours_memory = ours_tool + dp23
agents = {k: v for k, v in agents.items() if v}


def loss(runs, kind):
    per = defaultdict(float)
    count = defaultdict(int)
    for cases in runs:
        for c in cases:
            if c["kind"] == kind:
                per[c["category"]] += (1 - c["score"]) / len(runs)
                count[c["category"]] += 1
    return per, {k: v / len(runs) for k, v in count.items()}


lines = [f"# Family gaps: our code against the top agents (bench 15)", "",
         f"Our code: {len(ours_tool)} runs on the tool side (v8 live + local seed 5119), {len(ours_memory)} on the memory side (plus DrPresident v23).",
         f"Others: {', '.join(f'{k} ({len(v)})' for k, v in sorted(agents.items()))}.", ""]
for kind, ours in (("tool", ours_tool), ("memory", ours_memory)):
    mine, n_per_run = loss(ours, kind)
    others = {name: loss(runs, kind)[0] for name, runs in agents.items()}
    cats = sorted(set(mine) | {c for o in others.values() for c in o}, key=lambda c: -mine.get(c, 0))
    names = sorted(others)
    lines += [f"## {kind}", "", "| family | cases/run | ours | " + " | ".join(names) + " | best other | gap |", "|---|---|---|" + "---|" * len(names) + "---|---|"]
    total_gap = 0.0
    for c in cats:
        best = min(o.get(c, 0.0) for o in others.values())
        gap = mine.get(c, 0.0) - best
        if mine.get(c, 0) < 0.15 and max(o.get(c, 0) for o in others.values()) < 0.3:
            continue
        real = mine.get(c, 0) >= 0.3 and best <= mine.get(c, 0) / 3
        total_gap += max(gap, 0) if real else 0
        lines.append(f"| {c}{' **gap**' if real else ''} | {n_per_run.get(c, 0):.1f} | {mine.get(c, 0):.2f} | " + " | ".join(f"{others[n].get(c, 0):.2f}" for n in names) + f" | {best:.2f} | {gap:+.2f} |")
    lines += ["", f"Sum of real {kind} gaps: {total_gap:.2f} points a run ({total_gap * (0.005 if kind == 'tool' else 0.002):.4f} composite).", ""]
open(OUT, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
