"""bauni v6 case shape: for a case, every stored record naming an item, a distractor, or the asked person, plus the
episode descriptors ("school gates", "taxi") and how many other records reuse them.

    python3 -I live/bauni6_shape.py PACK.json [CASE_INDEX...]
"""
import json, sys, re, collections
p = json.load(open(sys.argv[1]))
idx = [int(a) for a in sys.argv[2:]] or [0]
recs = []
for wi, w in enumerate(p["memory_waves"]):
    for x in w["pairs"]:
        recs.append((wi, w["user_id"], x["timestamp"], x["pair_id"], x["prompt"]))
print("records", len(recs), "users", collections.Counter(r[1] for r in recs))
for i in idx:
    c = p["cases"][i]
    print("\n=====", c["id"], "user", c["user_id"], "Q:", c["question"])
    print("items", c["answer_items"], "distractors", c["distractor_answers"])
    name = re.search(r"does (.+?) go to", c["question"]).group(1)
    keys = [name] + c["answer_items"] + c["distractor_answers"]
    hits = [r for r in recs if r[1] == c["user_id"] and any(k in r[4] for k in keys)]
    for r in sorted(hits, key=lambda r: r[2]):
        tag = "EV" if r[3] in c["evidence_pair_ids"] else "  "
        print(f"  {tag} w{r[0]} {r[2]} {r[3]}: {r[4]}")
    # the records right before each distractor record (its own episode)
    for d in c["distractor_answers"]:
        for r in recs:
            if r[1] == c["user_id"] and d in r[4]:
                prev = [q for q in recs if q[1] == r[1] and q[2] < r[2]]
                prev = sorted(prev, key=lambda q: q[2])[-2:]
                for q in prev:
                    print(f"     before {d}: {q[2]} {q[4]}")
