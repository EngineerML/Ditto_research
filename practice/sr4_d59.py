"""Official per-case scores per agent in the staged-records-v4 run, plus d59's misses."""
import json, collections
run = "/home/bittensor/ditto/practice/generator/20261115T232734Z"
r = json.load(open(f"{run}/run-pack-1-r0.json"))
pack = json.load(open(f"{run}/packs/pack-1.json"))
byq = {c["question"]: c for c in pack["cases"]}
seed = r["score"]["seeds"][0]
c0 = seed["cases"][0]
print("case keys", list(c0))
for agent in ("v6", "d59"):
    dist = collections.Counter()
    for line in open(f"{run}/trace/pack-1-r0/{agent}/trace.jsonl"):
        t = json.loads(line)
        c = byq[t["user_input"]]
        reply = (t.get("final_text") or "").replace("\n", " ")
        got = [i for i in c["answer_items"] if i.lower() in reply.lower()]
        bad = [d for d in c["distractor_answers"] if d.lower() in reply.lower()]
        decline = any(w in reply.lower() for w in ("no record", "couldn't find", "couldn’t find", "unknown", "don't have"))
        key = "distractor" if bad else f"{len(got)}/2" + (" +decline" if decline else "")
        dist[key] += 1
        if agent == "d59" and (bad or len(got) < 2):
            print(f"  d59 miss {c['id']} {c['question_type']} {key} | {reply[:200]}")
    print(agent, dict(dist))
