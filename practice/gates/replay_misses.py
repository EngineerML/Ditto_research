"""Wrong answers of a graded replay: shape, relation, expected, the reply, the grader's notes, and the ledger's NOW lines.

    python3 practice/gates/replay_misses.py REPLAY.json [SEED]"""
import json
import re
import sys

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
from v14_oracle import shapes  # noqa: E402

replay = json.load(open(sys.argv[1]))
only = int(sys.argv[2]) if len(sys.argv) > 2 else None
for m in replay:
    if m["new_score"] >= 0.5 or (only and m["seed"] != only):
        continue
    s = shapes(m["seed"])[m["id"]]
    now = [line for line in (m.get("ledger") or "").splitlines() if re.match(r"\s*(NOW|LABEL)\b", line)]
    print(f"--- {m['seed']} {s.label} {s.domain} {s.relation} expected {m['expected']!r} (traced v7.1 score {m['score']})")
    print(f"    reply: {m['new_final_text'][-300:]!r}")
    print(f"    notes: {m['new_notes'][:2]}")
    print(f"    ledger: {now[:8]}")
