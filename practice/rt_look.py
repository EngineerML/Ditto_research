"""Show, for one case of a generator-panel run, the composed prompt around the asked name and the relay, plus the reply.

    python3 practice/rt_look.py RUN_DIR PACK_RUN AGENT CASE_ID
"""
import json, sys, glob
run, pr, agent, cid = sys.argv[1:5]
pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
case = next(c for c in pack["cases"] if c["id"] == cid)
pairs = {x["pair_id"]: x for w in pack["memory_waves"] for x in w["pairs"]}
relay = pairs[case["evidence_pair_ids"][-1]]["prompt"]
for line in open(f"{run}/trace/{pr}/{agent}/trace.jsonl"):
    t = json.loads(line)
    if t["user_input"] != case["question"]:
        continue
    print("Q:", case["question"], "| items", case["answer_items"])
    print("events:", [e for e in t.get("events", []) if "phrase" in e or "follow" in e or "list" in e.lower()])
    for i, call in enumerate(t.get("calls") or []):
        msgs = call.get("messages") or call.get("request", {}).get("messages") or []
        text = "\n".join(m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content")) for m in msgs)
        print(f"--- call {i}: {len(text)} chars, relay present: {relay[:40] in text}")
        k = text.find(relay[:40])
        if k >= 0:
            print(text[max(0, k - 900):k + 400])
        tail = text[-2500:]
        print("... tail:\n", tail)
        out = call.get("response") or call.get("output") or ""
        print("--- output:", str(out)[:600])
    print("FINAL:", t.get("final_text"))
