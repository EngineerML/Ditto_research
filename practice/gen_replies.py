"""Show each agent's reply on cases of one question type in a generator panel run, with items / distractors and the
grader's score when the trace carries one.
    python3 practice/gen_replies.py RUN_DIR QTYPE_SUBSTRING [MAX_CASES]
"""
import json, os, sys
run, want = sys.argv[1], sys.argv[2]
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 4
shown = 0
for pr in sorted(os.listdir(f"{run}/trace")):
    pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
    byq = {c["question"]: c for c in pack["cases"]}
    rows = {}
    for agent in sorted(os.listdir(f"{run}/trace/{pr}")):
        path = f"{run}/trace/{pr}/{agent}/trace.jsonl"
        if not os.path.exists(path):
            continue
        for line in open(path):
            t = json.loads(line)
            c = byq[t["user_input"]]
            if want in c.get("question_type", ""):
                rows.setdefault(t["user_input"], []).append((agent, t))
    for q, items in rows.items():
        if shown >= cap:
            break
        shown += 1
        c = byq[q]
        print(f"== {c['question_type']} | {q}\n   items {c['answer_items']} traps {c['distractor_answers']}")
        for agent, t in items:
            sc = t.get("score", t.get("grade", {}).get("score") if isinstance(t.get("grade"), dict) else None)
            print(f"   [{agent} {sc}] {(t.get('final_text') or '').strip()[:400]!r}")
