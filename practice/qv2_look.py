"""One querverweis case: events, then each call's notes after the records (everything after the records block) and output.

    python3 practice/qv2_look.py RUN_DIR PACK_RUN AGENT CASE_ID
"""
import json, sys
run, pr, agent, cid = sys.argv[1:5]
pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
case = next(c for c in pack["cases"] if c["id"] == cid)
for line in open(f"{run}/trace/{pr}/{agent}/trace.jsonl"):
    t = json.loads(line)
    if t["user_input"] != case["question"]:
        continue
    print("Q:", case["question"], "| items", case["answer_items"], "| traps", case["distractor_answers"])
    for e in t.get("events") or []:
        print("  event:", str(e)[:220])
    for i, call in enumerate(t.get("calls") or []):
        msgs = call.get("messages") or call.get("request", {}).get("messages") or []
        print(f"--- call {i}: roles {[m.get('role') for m in msgs]}")
        for m in msgs:
            text = m["content"] if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
            if m.get("role") == "system":
                print("  [system]", len(text), "chars")
                continue
            k = text.find("]}}")
            print("  [" + str(m.get("role")) + "] records part", k, "chars; after records:\n", text[k + 3:][:3500] if k >= 0 else text[:3500])
        out = call.get("response") or call.get("output") or call.get("text") or ""
        print("--- output:", str(out)[:1200])
    print("FINAL:", t.get("final_text"))
