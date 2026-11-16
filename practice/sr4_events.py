"""Events and call count of chosen cases in a generator-panel trace."""
import json, sys
run, packdir, agent = sys.argv[1], sys.argv[2], sys.argv[3]
want = set(sys.argv[4:])
pack = json.load(open(f"{run}/packs/" + __import__("os").listdir(f"{run}/packs")[0]))
byq = {c["question"]: c for c in pack["cases"]}
for line in open(f"{run}/trace/{packdir}/{agent}/trace.jsonl"):
    t = json.loads(line)
    c = byq[t["user_input"]]
    if c["id"] not in want:
        continue
    print("==", c["id"], "keys", sorted(t)[:20])
    print("  Q:", c["question"])
    for e in t.get("events") or []:
        print("   ev:", str(e)[:220])
    print("  calls", len(t.get("calls") or []))
