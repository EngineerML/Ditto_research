#!/usr/bin/env python3
"""request_kind / product_tool / live handling of one lab tree over the cached bench-15 datasets, as JSON lines; run once
per tree and compare. Free: no model call.

    .venv/bin/python practice/gates/hint_compare.py LAB_DIR OUT.jsonl
"""
import glob
import json
import sys

sys.path.insert(0, sys.argv[1])
from app import thint  # noqa: E402

with open(sys.argv[2], "w") as out:
    for path in sorted(glob.glob("/home/bittensor/ditto/.cache/datasets/v15_s*_salt0_full.json")):
        d = json.load(open(path))
        names = [t["name"] for t in d["catalog"] if not t.get("description", "").rstrip().endswith("connector to be linked in Settings.")]
        rows = [(c["id"], "tool", c["category"], c["prompt"], [e["name"] for e in c.get("expected_tools") or []]) for c in d["tool_cases"]]
        rows += [(c["id"], "memory", c["question_type"], c["question"], []) for c in d["memory_cases"]]
        for cid, kind, category, text, expected in rows:
            k = thint.request_kind(text, names)
            live = k in ("", "web") and thint.live_lookup(text) if hasattr(thint, "live_lookup") else False
            out.write(json.dumps({"seed": d["seed"], "id": cid, "kind": kind, "category": category, "expected": expected,
                                  "request_kind": k, "product": thint.product_tool(text, names), "hint": thint.tool_hint(text, names)[:160], "live": live}) + "\n")
