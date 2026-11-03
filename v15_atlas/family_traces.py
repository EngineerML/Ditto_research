#!/usr/bin/env python3
"""v8's replies for chosen memory families on a local paid run, matched by served text, with score, grader notes,
expected answer and distractors.

    python3 v15_atlas/family_traces.py RUN_DIR SEED family [family ...]
"""
import json
import sys

ROOT = "/home/bittensor/ditto"
run, seed, families = sys.argv[1], sys.argv[2], set(sys.argv[3:])
rep = {c["case_id"]: c for c in json.load(open(run + "/report.json"))["report"]["per_case"]}
ds = {c["id"]: c for c in json.load(open(f"{ROOT}/.cache/datasets/v15_s{seed}_salt0_full.json"))["memory_cases"]}
served = {c["id"]: c["question"] for c in json.load(open(f"{ROOT}/.cache/served/v15_s{seed}_served.json"))["memory_cases"]}
traces = {}
for line in open(run + "/trace.jsonl"):
    t = json.loads(line)
    traces.setdefault(t["user_input"].strip(), []).append(t)
for cid, mc in sorted(ds.items(), key=lambda kv: (kv[1]["question_type"], -rep.get(kv[0], {}).get("score", 1))):
    if mc["question_type"] not in families:
        continue
    r = rep.get(cid, {})
    t = (traces.get(served[cid].strip()) or [{}])[0]
    print("=" * 110)
    print(f"{mc['question_type']}  score {r.get('score')}  notes {[n for n in r.get('notes') or [] if 'validator' not in n]}")
    print("Q:", served[cid][:240])
    print("expected:", mc["expected_answer"], "| distractors:", mc.get("distractor_answers"))
    print(f"lane {t.get('lane')} path {t.get('path')} model_calls {t.get('model_calls')}")
    print("REPLY:", (t.get("final_text") or "").replace("\n", " ")[:420])
