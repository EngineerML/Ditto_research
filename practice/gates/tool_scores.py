"""Per-question scores of a tool-questions run, by category, with every miss listed.

    python3 practice/gates/tool_scores.py RUN [OTHER_RUN]

With a second run (another version or bench of the same seed), questions with the same text are paired and the
score differences listed."""
import json
import sys
from collections import defaultdict


def load(run: str) -> tuple[list[dict], dict[str, str]]:
    report = json.load(open(run + "/report.json"))
    parts = report.get("partial") or report.get("report", {}).get("per_case") or []
    trace = {}
    try:
        for line in open(run + "/trace.jsonl"):
            case = json.loads(line)
            trace[case["case_id"]] = case
    except FileNotFoundError:
        pass
    return [p for p in parts if p.get("kind") == "tool"], trace


tools, trace = load(sys.argv[1])
scores = [p.get("score") or 0 for p in tools]
print(f"{len(tools)} tool questions: mean score {sum(scores) / max(len(scores), 1):.4f}; "
      f"zero {sum(1 for s in scores if s == 0)}, partial {sum(1 for s in scores if 0 < s < 1)}, full {sum(1 for s in scores if s >= 1)}")
cost = [p.get("inference_cost") for p in tools if isinstance(p.get("inference_cost"), (int, float))]
if cost:
    print(f"inference cost factor: mean {sum(cost) / len(cost):.4f}")
by = defaultdict(list)
for p in tools:
    by[p.get("category")].append(p.get("score") or 0)
print("categories below 1:")
for cat, s in sorted(by.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
    if min(s) < 1:
        print(f"  {cat:45} n={len(s)} mean={sum(s) / len(s):.3f}")
print("misses:")
for p in tools:
    if (p.get("score") or 0) < 1:
        case = trace.get(p["case_id"], {})
        print(f"- {p.get('score'):.3f} [{p.get('category')}] expected={p.get('expected')} called={p.get('called')} "
              f"lane={case.get('lane')} | {case.get('user_input', '')[:150]}")
        notes = p.get("notes")
        if notes:
            print(f"    notes: {str(notes)[:300]}")
if len(sys.argv) > 2:
    other, other_trace = load(sys.argv[2])
    text = {trace.get(p["case_id"], {}).get("user_input"): p for p in tools}
    pairs = [(text[other_trace.get(q["case_id"], {}).get("user_input")], q) for q in other
             if other_trace.get(q["case_id"], {}).get("user_input") in text]
    a = sum(p.get("score") or 0 for p, _ in pairs)
    b = sum(q.get("score") or 0 for _, q in pairs)
    print(f"\npaired with {sys.argv[2]}: {len(pairs)} questions, sum {a:.2f} here vs {b:.2f} there")
    for p, q in pairs:
        if abs((p.get("score") or 0) - (q.get("score") or 0)) > 1e-9:
            print(f"  {p.get('score'):.3f} vs {q.get('score'):.3f} [{p.get('category')}] {trace[p['case_id']]['user_input'][:120]}")
