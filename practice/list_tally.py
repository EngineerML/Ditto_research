"""Two-item list tally for a generator-panel run, normalised like the grader (lower case, any Unicode space run -> one
space, bounded containment): per pack and agent, mean and 2/2, 1/2, 0/2, distractor counts.

    python3 practice/list_tally.py RUN_DIR AGENT [AGENT...]
"""
import json, os, re, sys, collections
run, agents = sys.argv[1], sys.argv[2:]
DECL = ("no record", "couldn't find", "couldn’t find", "unknown", "don't have", "not recorded")
norm = lambda s: " ".join(s.lower().split())
hit = lambda text, phrase: re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None
for pr in sorted(os.listdir(f"{run}/trace")):
    pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
    byq = {c["question"]: c for c in pack["cases"]}
    for agent in agents:
        path = f"{run}/trace/{pr}/{agent}/trace.jsonl"
        if not os.path.exists(path):
            continue
        dist, tot, n = collections.Counter(), 0.0, 0
        for line in open(path):
            t = json.loads(line)
            c = byq[t["user_input"]]
            reply = norm(t.get("final_text") or "")
            got = [i for i in c["answer_items"] if hit(reply, i)]
            bad = [x for x in c["distractor_answers"] if hit(reply, x)]
            dec = any(w in reply for w in DECL)
            s = 0.0 if bad or dec else len(got) / len(c["answer_items"])
            tot += s
            n += 1
            dist["distractor" if bad else f"{len(got)}/{len(c['answer_items'])}" + (" +decline" if dec else "")] += 1
        print(f"{pr:10} {agent:5} mean {tot / n:.2f} over {n}  {dict(dist)}")
