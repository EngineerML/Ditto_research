#!/usr/bin/env python3
"""Answerable memory cases zeroed by the grader's decline lexicon ("abstained on an answerable question"), over every
local real-model full run, with the reply text and whether the expected value was in it.

    python3 practice/gates/decline_hits.py [OUT.jsonl]
"""
import glob
import json
import os
import re
import sys
from collections import Counter

ROOT = "/home/bittensor/ditto"
NOTE = "abstained on an answerable question"
rows, runs = [], 0
for rep_path in sorted(glob.glob(f"{ROOT}/practice/*_full/report.json")):
    run = os.path.dirname(rep_path)
    try:
        top = json.load(open(rep_path))
        rep = top["report"]
    except Exception:
        continue
    rep["bench_version"] = top.get("bench_version")
    mem = [c for c in rep.get("per_case") or [] if c.get("kind") == "memory"]
    if not mem or sum(c["score"] for c in mem) / len(mem) < 0.6 or not os.path.exists(run + "/trace.jsonl"):
        continue  # mock or broken runs
    runs += 1
    seed, bench = rep.get("seed"), rep.get("bench_version")
    ds_path = f"{ROOT}/.cache/datasets/v{bench}_s{seed}_salt0_full.json"
    ds = {c["id"]: c for c in json.load(open(ds_path))["memory_cases"]} if os.path.exists(ds_path) else {}
    traces = [json.loads(line) for line in open(run + "/trace.jsonl")]
    for c in mem:
        if not any(NOTE in n for n in c.get("notes") or []):
            continue
        mc = ds.get(c["case_id"], {})
        question = mc.get("question", "")
        words = set(re.findall(r"\w+", question.lower()))
        best = max(traces, key=lambda t: len(words & set(re.findall(r"\w+", t["user_input"].lower())))) if traces and question else {}
        reply = best.get("final_text") or ""
        expected = mc.get("expected_answer") or ""
        rows.append({"run": os.path.basename(run), "bench": bench, "type": c["category"], "expected": expected,
                     "value_in_reply": bool(expected) and expected.lower() in reply.lower(), "path": best.get("path"),
                     "lane": best.get("lane"), "reply": reply})
print(f"real-model full runs: {runs}; answerable cases zeroed by the decline lexicon: {len(rows)} ({len(rows) / max(runs, 1):.2f} per run)")
print("with the expected value in the reply:", sum(r["value_in_reply"] for r in rows))
print("by type:", dict(Counter(r["type"] for r in rows).most_common()))
print("by path:", dict(Counter(str(r["path"]) for r in rows)))
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as out:
        for r in rows:
            out.write(json.dumps(r) + "\n")
