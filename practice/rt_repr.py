"""Print repr of final replies for given case ids in a run trace (to spot odd spaces or characters).

    python3 practice/rt_repr.py RUN_DIR PACK_RUN AGENT CASE_ID [...]
"""
import json, sys
run, pr, agent, *ids = sys.argv[1:]
pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
want = {c["question"]: c["id"] for c in pack["cases"] if c["id"] in ids}
for line in open(f"{run}/trace/{pr}/{agent}/trace.jsonl"):
    t = json.loads(line)
    if t["user_input"] in want:
        print(want[t["user_input"]], repr(t.get("final_text")))
