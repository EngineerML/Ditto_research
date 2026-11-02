"""Routing of one harness on the same seed at bench 14 and bench 15 (mock-model runs), question by question.

    python3 practice/gates/route_v14_v15.py V14_RUN V15_RUN

Served questions are deterministic per seed and version. Between versions only the dataset dates move (the v15
epoch is a month later), so requests are paired exactly where the text is equal, then by the closest text with
digits ignored. For every pair the lane (name:reason) and path (program, topic, records, action) are compared,
and every moved request is listed with its question and tool count."""
import difflib
import json
import re
import sys
from collections import Counter

DIGITS = re.compile(r"\d+")


def load(run: str) -> list[dict]:
    return [json.loads(line) for line in open(run + "/trace.jsonl")]


def key(text: str) -> str:
    return DIGITS.sub("#", text)


a, b = load(sys.argv[1]), load(sys.argv[2])
print(f"v14 {len(a)} requests, tools per request {Counter(len(t.get('tools') or []) for t in a).most_common(2)}")
print(f"v15 {len(b)} requests, tools per request {Counter(len(t.get('tools') or []) for t in b).most_common(2)}")
pairs, left = [], list(range(len(b)))
by_text = {}
for j in left:
    by_text.setdefault(b[j]["user_input"], []).append(j)
unpaired = []
for t in a:
    js = by_text.get(t["user_input"])
    if js:
        j = js.pop(0)
        pairs.append((t, b[j], 1.0))
        left.remove(j)
    else:
        unpaired.append(t)
by_key = {}
for j in left:
    by_key.setdefault(key(b[j]["user_input"]), []).append(j)
fuzzy = []
for t in unpaired:
    js = by_key.get(key(t["user_input"]))
    if js:
        j = js.pop(0)
        pairs.append((t, b[j], 0.99))
        left.remove(j)
    else:
        fuzzy.append(t)
for t in fuzzy:
    if not left:
        break
    j = max(left, key=lambda j: difflib.SequenceMatcher(None, t["user_input"], b[j]["user_input"]).ratio())
    pairs.append((t, b[j], difflib.SequenceMatcher(None, t["user_input"], b[j]["user_input"]).ratio()))
    left.remove(j)
print(f"paired {len(pairs)}: exact {sum(1 for p in pairs if p[2] == 1.0)}, same but digits {sum(1 for p in pairs if p[2] == 0.99)}, "
      f"closest text {sum(1 for p in pairs if p[2] < 0.99)} (lowest ratio {min((p[2] for p in pairs), default=1):.2f}); unpaired v15 {len(left)}")


def route(t):
    return (t.get("lane"), t.get("path"))


same = [p for p in pairs if route(p[0]) == route(p[1])]
moved = [p for p in pairs if route(p[0]) != route(p[1])]
print(f"\nsame lane and path: {len(same)} | moved: {len(moved)}")
print("paths v14:", dict(Counter(t.get("path") for t in a)), "| v15:", dict(Counter(t.get("path") for t in b)))
print("moves (v14 lane/path -> v15 lane/path):")
for (l14, p14, l15, p15), n in Counter((p[0].get("lane"), p[0].get("path"), p[1].get("lane"), p[1].get("path")) for p in moved).most_common():
    print(f"  {n:3}  {l14}/{p14} -> {l15}/{p15}")

def side(t):
    return ((t.get("lane") or ":").split(":")[0], t.get("path"))


# A reason label change inside the same lane and path leaves what the request goes through the same; a change of lane
# name or path is a real move. Pairs below 0.9 text similarity are not the same question (tool prompts are drawn
# against the catalog), so they are listed apart.
sure = [p for p in moved if p[2] >= 0.9]
real = [p for p in sure if side(p[0]) != side(p[1])]
print(f"\nmoved with the same lane name and path (reason label only): {sum(1 for p in sure if side(p[0]) == side(p[1]))}")
print(f"real moves (lane name or path changed), pairs at >= 0.9 similarity: {len(real)}")
for t14, t15, ratio in real:
    print(f"- {t14.get('lane')}/{t14.get('path')} -> {t15.get('lane')}/{t15.get('path')} | {t15['user_input'][:170]}")
loose = [p for p in pairs if p[2] < 0.9]
print(f"\npairs under 0.9 similarity (different questions, not compared): {len(loose)}")
print("routes of those, v14:", dict(Counter(side(p[0]) for p in loose)), "| v15:", dict(Counter(side(p[1]) for p in loose)))
