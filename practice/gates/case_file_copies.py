"""Records of program case files grouped by filing time: are the rows sharing one timestamp copies of one event?

For each seed, each case-file token of a program question: records holding that token, grouped by timestamp.
Prints group sizes overall and, for a few files, the rows of each group."""
import json
import re
import sys
from collections import Counter, defaultdict

SCOPE = re.compile(r"\bc[0-9a-f]{16}\b")
seed = sys.argv[1]
show = sys.argv[2:] if len(sys.argv) > 2 else []
data = json.load(open(f"/home/bittensor/ditto/.cache/datasets/v14_s{seed}_salt0_full.json"))
print("keys:", list(data)[:12])
cases = [c for c in data["memory_cases"] if c["question_type"] in ("v13-open-program", "v13-personal-program")]
print("case keys:", list(cases[0])[:20])
records = []


def collect(node):
    if isinstance(node, dict):
        if "prompt" in node and "timestamp" in node:
            records.append(node)
        else:
            for value in node.values():
                collect(value)
    elif isinstance(node, list):
        for value in node:
            collect(value)


collect(data["memory_waves"])
if not records:
    for c in cases[:1]:
        print({k: str(v)[:200] for k, v in c.items()})
print(len(records), "records; record keys:", list(records[0]) if records else None)
tokens = sorted({SCOPE.search(c["question"]).group(0) for c in cases if SCOPE.search(c["question"])})
sizes = Counter()
mixed = 0
for token in tokens:
    rows = [r for r in records if token in (r.get("prompt") or "") + (r.get("response") or "")]
    by_time = defaultdict(list)
    for r in rows:
        by_time[r.get("timestamp")].append(r)
    for ts, group in by_time.items():
        sizes[len(group)] += 1
    if any(word.lower() in " ".join(r["prompt"].lower() for r in rows) for word in show):
        print(f"=== {token}: {len(rows)} rows, {len(by_time)} timestamps")
        for ts in sorted(by_time):
            for r in by_time[ts]:
                print(f"  {ts}  {r['prompt'][:150]!r}")
print("rows per timestamp:", dict(sizes))
