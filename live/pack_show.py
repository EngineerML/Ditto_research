"""Show N cases of a pack: question, expected/items, distractors, and the evidence pair prompts in wave order.

    python3 -I live/pack_show.py PACK.json [N] [START]
"""
import json, sys
p = json.load(open(sys.argv[1]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
pairs = {}
for wi, w in enumerate(p["memory_waves"]):
    for x in w["pairs"]:
        pairs[x["pair_id"]] = (w.get("wave", wi), w.get("user_id", "-"), x)
kinds = {}
for c in p["cases"]:
    kinds[c["question_type"]] = kinds.get(c["question_type"], 0) + 1
print("question types", kinds)
for c in p["cases"][start:start + n]:
    print("\n=====", c["id"], c["question_type"], c["answer_kind"], "user", c.get("user_id"), "after wave", c.get("run_after_wave"))
    print("Q:", c["question"])
    print("expected:", c["expected_answer"], "| items:", c.get("answer_items"), "| distractors:", c["distractor_answers"], "| guard:", c.get("dump_guard"))
    for pid in c["evidence_pair_ids"]:
        wv, u, x = pairs[pid]
        print(f"  [w{wv} {u} {x['timestamp']}] P: {x['prompt']}\n      R: {x['response'][:200]}")
