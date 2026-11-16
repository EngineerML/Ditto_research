"""querverweis: every distractor's records for the first N cases of a pack, to see each trap kind; and the question forms.

    python3 -I practice/qv2_traps.py PACK.json [N]
"""
import json, re, sys, collections
p = json.load(open(sys.argv[1]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
recs = [x for w in p["memory_waves"] for x in w["pairs"]]
forms = collections.Counter(re.sub(r"does .+? (get|buy|swim|climb|watch|work|go|eat|see|play|take)", r"does <who> \1", re.sub(r"^Which [\w ]+? does", "Which <X> does", c["question"])) for c in p["cases"])
for f, k in forms.most_common(12):
    print(k, f)
for c in p["cases"][:n]:
    print(f"\n== {c['id']} {c['question']}  items {c['answer_items']}")
    for d in c["distractor_answers"]:
        for r in recs:
            if d in r["prompt"]:
                print(f"   TRAP {d}: [{r['timestamp'][:10]}] {r['prompt'][:170]}")
