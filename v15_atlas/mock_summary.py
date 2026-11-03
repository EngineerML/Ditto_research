#!/usr/bin/env python3
"""Final lane and path per family from the mock bench (the harness's real routing, mock model), matched to the served
text by exact input.

    python3 v15_atlas/mock_summary.py v15_atlas/mock_runs_<tag>.txt v15_atlas/mock_<tag>
"""
import json
import sys
from collections import Counter, defaultdict

ROOT = "/home/bittensor/ditto"
MEMORY_TOOLS = {"search_memories", "fetch_memories", "search_subjects", "search_memories_in_subjects"}
fam = defaultdict(Counter)
unmatched = total = 0
runs = [line.split() for line in open(sys.argv[1]) if len(line.split()) == 2]
for seed, run in runs:
    d = json.load(open(f"{ROOT}/.cache/datasets/v15_s{seed}_salt0_full.json"))
    served = json.load(open(f"{ROOT}/.cache/served/v15_s{seed}_served.json"))
    meta = {c["id"]: ("tool", c["category"], [e["name"] for e in c.get("expected_tools") or []]) for c in d["tool_cases"]}
    meta |= {c["id"]: ("memory", c["question_type"], []) for c in d["memory_cases"]}
    by_text = defaultdict(list)
    for c in served["tool_cases"]:
        by_text[c["prompt"].strip()].append(c["id"])
    for c in served["memory_cases"]:
        by_text[c["question"].strip()].append(c["id"])
    for line in open(run + "/trace.jsonl"):
        t = json.loads(line)
        total += 1
        ids = by_text.get(t["user_input"].strip())
        if not ids:
            unmatched += 1
            continue
        kinds = {meta[i][:2] for i in ids}
        if len(kinds) > 1:
            fam[("shared", "|".join(sorted(k[1] for k in kinds)))]["n"] += 1
            continue
        kind, family, expected = meta[ids[0]]
        lane = str(t.get("lane"))
        s = fam[(kind, family)]
        s["n"] += 1
        s["lane " + lane] += 1
        s["path " + str(t.get("path"))] += 1
        if kind == "tool" and lane.startswith("records") and not set(expected) <= MEMORY_TOOLS:
            s["unexpected"] += 1
        if kind == "memory" and lane.startswith("action"):
            s["unexpected"] += 1
        if "request hint" in (t.get("events") or []):
            s["hint"] += 1
lines = [f"# Mock bench: {len(runs)} seeds, {total} traced requests ({unmatched} unmatched)", "",
         "Final lane after every store-dependent re-route (identifier, topic, answer-form). Unexpected = a tool case in the",
         "records lane whose expected tools are not memory reads, or a memory question in the action lane.", "",
         "| kind | family | n/run | unexpected | top lanes | top paths | hint |", "|---|---|---|---|---|---|---|"]
out = {}
for (kind, family), s in sorted(fam.items(), key=lambda kv: (-kv[1]["unexpected"] / max(kv[1]["n"], 1), kv[0])):
    n = s["n"]
    lanes = Counter({k[5:]: v for k, v in s.items() if k.startswith("lane ")}).most_common(2)
    paths = Counter({k[5:]: v for k, v in s.items() if k.startswith("path ")}).most_common(2)
    out[family] = {"kind": kind, "n": n, "unexpected": s["unexpected"], "lanes": dict(lanes), "paths": dict(paths), "hint": s["hint"]}
    lines.append(f"| {kind} | {family} | {n / len(runs):.1f} | {100 * s['unexpected'] / n:.0f}% | {', '.join(f'{k} {v}' for k, v in lanes)} | {', '.join(f'{k} {v}' for k, v in paths)} | {s['hint']} |")
open(sys.argv[2] + ".md", "w").write("\n".join(lines) + "\n")
json.dump(out, open(sys.argv[2] + ".json", "w"), indent=1)
print("\n".join(lines[:30]))
