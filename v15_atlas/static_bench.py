#!/usr/bin/env python3
"""Static bench (free): run a lab tree's request-only rules over every request of the atlas corpus.

    .venv/bin/python v15_atlas/static_bench.py LAB_DIR OUT.jsonl

Text is the SERVED text (.cache/served/, from v15_atlas/build_served.sh), not the dataset files' typo'd text.
Per request: the connector step (kept, left out, kept as linked), the first-stage lane (lane.classify plus the
tool-hint and own-setting overrides of CaseRunner.run), request_kind, product_tool, live_lookup and qtype's
question_kind. Store-dependent re-routes (identifier, topic, answer-form) need the memory store and come from the
mock bench instead.
"""
import glob
import json
import re
import sys

sys.path.insert(0, sys.argv[1])
from app import thint  # noqa: E402
from app.available import usable  # noqa: E402
from app.config import Levers  # noqa: E402
from app.lane import ACTION, RECORDS, Lane, classify  # noqa: E402
from app.protocol import RunRequest, ToolDefinition  # noqa: E402
from app.qtype import question_kind  # noqa: E402

levers = Levers()
live_lookup = getattr(thint, "live_lookup", None)


def first_lane(text: str, tools: list[ToolDefinition]) -> Lane:
    lane = classify(text, tools, levers.typo_cues, preamble=levers.route_preamble, asking=levers.route_asking, anchor=levers.route_anchor, lexicon=levers.route_lexicon, operands=levers.route_operands, save=levers.route_save)
    names = [tool.name for tool in tools]
    if lane.name == RECORDS and thint.tool_kind(text, names):
        lane = Lane(ACTION, "tool-hint")
    if thint.request_kind(text, names) == "own-setting-stated":
        lane = Lane(ACTION, "setting-statement")
    return lane


ROOT = "/home/bittensor/ditto"
with open(sys.argv[2], "w") as out:
    for seed in [int(line) for line in open(f"{ROOT}/v15_atlas/corpus_seeds.txt") if line.strip()]:
        salt = 0
        d = json.load(open(f"{ROOT}/.cache/datasets/v15_s{seed}_salt0_full.json"))
        # The text a harness is served (no dataset typo pass); metadata and catalog come from the dataset by case id.
        served = json.load(open(f"{ROOT}/.cache/served/v15_s{seed}_served.json"))
        text = {c["id"]: c["prompt"] for c in served["tool_cases"]} | {c["id"]: c["question"] for c in served["memory_cases"]}
        catalog = [ToolDefinition(**{k: t[k] for k in ("name", "description", "parameters") if k in t}) for t in d["catalog"]]
        rows = [(c["id"], "tool", c["category"], text[c["id"]], [e["name"] for e in c.get("expected_tools") or []]) for c in d["tool_cases"]]
        rows += [(c["id"], "memory", c["question_type"], text[c["id"]], []) for c in d["memory_cases"]]
        for cid, kind, family, text, expected in rows:
            tools, left_out, stayed = usable(RunRequest(case_id=cid, user_input=text, tools=catalog))
            names = [tool.name for tool in tools]
            lane = first_lane(text, tools)
            rk = thint.request_kind(text, names)
            out.write(json.dumps({
                "seed": seed, "salt": salt, "id": cid, "kind": kind, "family": family, "expected": expected,
                "kept": len(tools), "left_out": left_out, "stayed": stayed,
                "lane": f"{lane.name}:{lane.reason}", "request_kind": rk, "product": thint.product_tool(text, names),
                "live": bool(live_lookup and rk in ("", "web") and live_lookup(text)), "qtype": question_kind(text),
                "chars": len(text),
            }) + "\n")
