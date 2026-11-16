"""Two-item list tally for a generator-panel run: per agent 2/2, 1/2, 0 (with decline), distractor; misses shown.

    python3 practice/sr4_score.py RUN_DIR PACK_DIR_NAME AGENT [AGENT...]
"""
import json, sys, collections, glob
run, packdir, agents = sys.argv[1], sys.argv[2], sys.argv[3:]
pack = json.load(open(glob.glob(f"{run}/packs/*.json")[0]))
byq = {c["question"]: c for c in pack["cases"]}
DECL = ("no record", "couldn't find", "couldn’t find", "unknown", "don't have", "not recorded")
for agent in agents:
    dist, tot, n = collections.Counter(), 0.0, 0
    for line in open(f"{run}/trace/{packdir}/{agent}/trace.jsonl"):
        t = json.loads(line)
        c = byq[t["user_input"]]
        reply = (t.get("final_text") or "").replace("\n", " ")
        got = [i for i in c["answer_items"] if i.lower() in reply.lower()]
        bad = [d for d in c["distractor_answers"] if d.lower() in reply.lower()]
        decline = any(w in reply.lower() for w in DECL)
        s = 0.0 if bad or decline else len(got) / len(c["answer_items"])
        tot += s
        n += 1
        key = "distractor" if bad else f"{len(got)}/2" + (" +decline" if decline else "")
        dist[key] += 1
        if s < 1:
            ev = [e for e in t.get("events") or [] if "number" in str(e)][:1]
            print(f"  {agent} {c['id']} {c['question_type']} {key} | {reply[:150]} | {ev}")
    print(f"{agent}: approx mean {tot / n:.2f} over {n}  {dict(dist)}")
