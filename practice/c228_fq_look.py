"""5FqQq9 paid run: per case gold, distractors and the reply; and for one failed case, the last model call's messages."""
import json, glob, sys
run = "/home/bittensor/ditto/practice/generator/20261115T071342Z"
pack = json.load(open(f"{run}/packs/fq-v2.json")) if glob.glob(f"{run}/packs/fq-v2.json") else json.load(open("/home/bittensor/ditto/.cache/miner_gens/packs/fq-v2/pack-1.json"))
byq = {c["question"]: c for c in pack["cases"]}
agent = sys.argv[1] if len(sys.argv) > 1 else "v5"
shown = 0
for line in open(f"{run}/trace/fq-v2-r0/{agent}/trace.jsonl"):
    t = json.loads(line)
    c = byq.get(t["user_input"])
    if not c:
        continue
    reply = (t.get("final_text") or "").replace("\n", " ")
    ok = c["expected_answer"].lower() in reply.lower()
    wrong = [d for d in c.get("distractor_answers") or [] if d.lower() in reply.lower()]
    print(f"{'OK ' if ok else 'BAD'} {c['id']:18} gold {c['expected_answer']:22} said-distractor {wrong} | {reply[:150]}")
    if not ok and shown < 1 and len(sys.argv) > 2:
        shown += 1
        calls = t.get("calls") or []
        print("   calls", len(calls), "keys", sorted(t)[:30])
        for m in (calls[-1].get("messages") if calls else []) or []:
            print("   ---", m.get("role"), "\n", str(m.get("content"))[:6000])
