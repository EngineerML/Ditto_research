#!/usr/bin/env python3
"""Per-case diff of two mock runs of the same seed: lane, path, whether a request hint was added, and the event list.

    python3 practice/gates/mock_diff.py RUN_A RUN_B
"""
import json
import sys
from collections import Counter


def load(run):
    rows = {}
    for line in open(run + "/trace.jsonl"):
        t = json.loads(line)
        rows.setdefault((t["user_id"], t["user_input"].strip()), t)
    return rows


a, b = load(sys.argv[1]), load(sys.argv[2])
# user ids are per-run uuids; pair by input text and order instead
by_text_a, by_text_b = {}, {}
for (u, text), t in a.items():
    by_text_a.setdefault(text, []).append(t)
for (u, text), t in b.items():
    by_text_b.setdefault(text, []).append(t)
moves, hints, events = Counter(), Counter(), Counter()
same = 0
for text, ta in by_text_a.items():
    for x, y in zip(ta, by_text_b.get(text, [])):
        lane_x, lane_y = str(x.get("lane")), str(y.get("lane"))
        hx = "request hint" in (x.get("events") or [])
        hy = "request hint" in (y.get("events") or [])
        if lane_x.split(":")[0] != lane_y.split(":")[0]:
            moves[(lane_x, lane_y)] += 1
        elif lane_x != lane_y:
            moves[("label " + lane_x, lane_y)] += 1
        if hx != hy:
            hints[(hx, hy, lane_y)] += 1
        ex = [e for e in (x.get("events") or []) if not e.startswith(("tool notes", "packet", "short path", "state reading"))]
        ey = [e for e in (y.get("events") or []) if not e.startswith(("tool notes", "packet", "short path", "state reading"))]
        if ex == ey and lane_x == lane_y:
            same += 1
        else:
            events[(tuple(sorted(set(ex) - set(ey)))[:3], tuple(sorted(set(ey) - set(ex)))[:3])] += 1
print(f"cases {len(a)} / {len(b)}; identical lane and events {same}")
print("lane changes:", dict(moves) or "none")
print("request hint added/removed (old, new, lane):", dict(hints) or "none")
print("event differences (only old, only new): count")
for k, n in events.most_common(12):
    print("  ", k, n)
