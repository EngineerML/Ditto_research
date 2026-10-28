"""A full v14 run while it runs: tool questions answered so far, and every memory answer so far graded with
grade.Memory, the running mean per 10, plus the conversational slices and split twin groups so far.

    .venv/bin/python tools/regrade/live_full.py RUN_DIR SEED

Memory traces are matched to their questions as tools/gate_review.py does (best text match first, a
case-file id counting double); tool traces are told apart by their lane.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from gate_review import CONV, assign, regrade  # noqa: E402
from lab import data  # noqa: E402

data.BENCH = 14
run, seed = Path(sys.argv[1]), int(sys.argv[2])
d = json.load(open(data.dataset_path(seed, 0, "full")))
traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")] if (run / "trace.jsonl").is_file() else []
tool_traces = [t for t in traces if str(t.get("lane", "")).startswith("action") and len(traces) <= len(d["tool_cases"])]
memory_traces = traces[len(d["tool_cases"]):] if len(traces) > len(d["tool_cases"]) else []
print(f"tool phase: {min(len(traces), len(d['tool_cases']))}/{len(d['tool_cases'])} answered")
if not memory_traces:
    sys.exit(0)
cases = {c["id"]: c for c in d["memory_cases"]}
matched = assign(cases, memory_traces)
order = {id(t): i for i, t in enumerate(memory_traces)}
done = sorted(matched.items(), key=lambda kv: order[id(kv[1])])
scores = dict(zip([cid for cid, _ in done], regrade([(cases[cid], t) for cid, t in done])))
total = 0.0
for i, (cid, _) in enumerate(done, 1):
    total += scores[cid]
    if i % 10 == 0 or i == len(done):
        print(f"memory {i:3d}/{len(cases)}  mean {total / i:.3f}")
slices = defaultdict(list)
groups = defaultdict(list)
for cid, s in scores.items():
    c = cases[cid]
    if c["question_type"] in CONV:
        slices[c["question_type"]].append(s >= 0.5)
    if c.get("twin_group"):
        groups[c["twin_group"]].append(s >= 0.999)
print("conversational so far: " + ", ".join(f"{k.split('-')[-1]} {sum(v)}/{len(v)}" for k, v in slices.items()))
full = {g: v for g, v in groups.items() if len(v) == 3}
split = sum(1 for v in full.values() if len(set(v)) > 1)
print(f"twin groups complete {len(full)}/13, split {split}")
