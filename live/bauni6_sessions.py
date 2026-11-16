"""bauni v6: do an intro record and its relay record share a session_id, and do distractor relays share a session with
anything naming the asked person? Also the gap in records between intro and relay.

    python3 -I live/bauni6_sessions.py PACK.json
"""
import json, sys, collections
p = json.load(open(sys.argv[1]))
pairs = {}
for w in p["memory_waves"]:
    for x in w["pairs"]:
        pairs[x["pair_id"]] = dict(x, user=w["user_id"])
order = sorted(pairs.values(), key=lambda x: (x["user"], x["timestamp"], x["pair_id"]))
pos = {x["pair_id"]: i for i, x in enumerate(order)}
by_sess = collections.defaultdict(list)
for x in pairs.values():
    by_sess[x["session_id"]].append(x["pair_id"])
print("sessions", len(by_sess), "sizes", collections.Counter(len(v) for v in by_sess.values()))
same, gaps, dsame = 0, collections.Counter(), 0
for c in p["cases"]:
    ev = [pairs[i] for i in c["evidence_pair_ids"]]
    intro, relay = ev[-2], ev[-1]
    same += intro["session_id"] == relay["session_id"]
    gaps[pos[relay["pair_id"]] - pos[intro["pair_id"]]] += 1
    name = c["question"].split(" does ")[1].split(" go to")[0]
    for d in c["distractor_answers"]:
        for x in pairs.values():
            if d in x["prompt"]:
                mates = [pairs[i]["prompt"] for i in by_sess[x["session_id"]] if i != x["pair_id"]]
                dsame += any(name in m for m in mates)
print("intro/relay same session:", same, "of", len(p["cases"]))
print("relay position minus intro position:", dict(sorted(gaps.items())))
print("distractor relays sharing a session with a record naming the asked person:", dsame)
c = p["cases"][0]
for i in c["evidence_pair_ids"]:
    print(i, pairs[i]["session_id"], pairs[i]["prompt"][:70])
