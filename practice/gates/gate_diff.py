"""Offline routing check: the short_answer gate of two harness copies on every traced request of the v8 runs.

    .venv/bin/python practice/gates/gate_diff.py OLD_SRC NEW_SRC [RUN_GLOB, % for *]

The user's notes come from the seed's dataset, so focus is rebuilt as the harness builds it (identifier_focus over
every note). The gate is the code of CaseRunner.short_answer up to the ShortPath call; requests without focus would
go to the topic path, which both copies share. No model calls."""
import glob
import importlib
import json
import sys
from collections import Counter


def load(src: str):
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]
    sys.path.insert(0, src)
    mods = {n: importlib.import_module(f"app.{n}") for n in ("lane", "packet", "short", "protocol", "config")}
    mods["retrieval"] = importlib.import_module("app.memory.retrieval")
    sys.path.remove(src)
    return mods


def gate(m, q: str, tools, lane_reason: str, pairs) -> str:
    cands = [m["retrieval"].Candidate(pair=p) for p in pairs]
    focus = m["packet"].identifier_focus(q, cands)
    if lane_reason == "statement" or not m["lane"].own_records_question(q, tools, **({"carried": bool(focus), "held": bool(focus)} if "held" in m["lane"].own_records_question.__code__.co_varnames else {"carried": bool(focus)})):
        return "records (gate)"
    if not focus:
        return "topic"
    if not m["short"].short_records(focus, m["config"].Settings.__dataclass_fields__["short_max_chars"].default):
        return "records (long)"
    if not m["short"].focus_token(q, focus):
        return "records (no token)"
    return "program"


old, new = load(sys.argv[1]), load(sys.argv[2])
total, moves = Counter(), Counter()
for run in sorted(glob.glob(sys.argv[3].replace("%", "*") if len(sys.argv) > 3 else "/home/bittensor/ditto/practice/2026110*_ditto-harness-v8_full_rerun")):
    try:
        seed = json.load(open(run + "/report.json")).get("seed")
        data = json.load(open(f"/home/bittensor/ditto/.cache/datasets/v14_s{seed}_salt0_full.json"))
        open(run + "/trace.jsonl").close()
    except (OSError, ValueError):
        continue
    pairs = {}
    for m in (old, new):
        pairs[id(m)] = [m["protocol"].MemoryPair(**p) for w in data["memory_waves"] if w["user_id"] == "miner" for p in w.get("pairs") or []]
    print(f"== seed {seed} ({run[-40:]})")
    for line in open(run + "/trace.jsonl"):
        t = json.loads(line)
        if not (t.get("lane") or "").startswith("records:"):
            continue
        q, reason = t["user_input"], t["lane"].split(":", 1)[1]
        a = gate(old, q, [old["protocol"].ToolDefinition(name=n) for n in t.get("tools") or []], reason, pairs[id(old)])
        b = gate(new, q, [new["protocol"].ToolDefinition(name=n) for n in t.get("tools") or []], reason, pairs[id(new)])
        total[(t.get("path"), a, b)] += 1
        if a != b:
            moves[(a, b)] += 1
            print(f"   {a} -> {b} | traced path {t.get('path')} | {q[:130]}")
print("\ntraced path, old gate, new gate: count")
for k, v in sorted(total.items(), key=str):
    print("  ", k, v)
print("moved:", dict(moves))
