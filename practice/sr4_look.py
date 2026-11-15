"""staged-records-v4 run: structure of the run json, per-agent official scores, and per case gold vs reply."""
import json, sys
run = sys.argv[1] if len(sys.argv) > 1 else "/home/bittensor/ditto/practice/generator/20261115T232734Z"
r = json.load(open(f"{run}/run-pack-1-r0.json"))
print("keys", list(r)[:20])
pack = json.load(open(f"{run}/packs/pack-1.json"))
byq = {c["question"]: c for c in pack["cases"]}
for agent in ("v6", "d59"):
    print("\n==", agent)
    tot = 0
    n = 0
    for line in open(f"{run}/trace/pack-1-r0/{agent}/trace.jsonl"):
        t = json.loads(line)
        c = byq.get(t["user_input"])
        if not c:
            continue
        reply = (t.get("final_text") or "").replace("\n", " ")
        got = [i for i in c["answer_items"] if i.lower() in reply.lower()]
        bad = [d for d in c["distractor_answers"] if d.lower() in reply.lower()]
        s = 0 if bad else len(got) / len(c["answer_items"])
        tot += s
        n += 1
        if agent == "v6" and n <= 35:
            print(f"  {c['id']} items {len(got)}/2 distractor {bad} | {reply[:170]}")
    print(f"  approx score {tot/n:.2f} over {n}")
for k, v in r.items():
    if k != "cases":
        print(k, str(v)[:600])
