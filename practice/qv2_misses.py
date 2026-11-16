"""querverweis misses: per case the reply, each missed item and each distractor named, with the stored records that
write it (so the trap or the binding is visible).

    python3 practice/qv2_misses.py RUN_DIR PACK_RUN AGENT [summary]
"""
import json, re, sys, collections
run, pr, agent = sys.argv[1:4]
summary = len(sys.argv) > 4
pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
recs = [x for w in pack["memory_waves"] for x in w["pairs"]]
byq = {c["question"]: c for c in pack["cases"]}
norm = lambda s: " ".join(s.lower().split())
hit = lambda text, phrase: re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None
kinds = collections.Counter()
for line in open(f"{run}/trace/{pr}/{agent}/trace.jsonl"):
    t = json.loads(line)
    c = byq[t["user_input"]]
    reply = norm(t.get("final_text") or "")
    missed = [i for i in c["answer_items"] if not hit(reply, i)]
    bad = [x for x in c["distractor_answers"] if hit(reply, x)]
    if not missed and not bad:
        continue
    if not summary:
        print(f"\n== {c['id']} Q: {c['question']}\n   reply: {(t.get('final_text') or '').strip()[:220]}")
    for tag, items in (("MISSED", missed), ("TRAP NAMED", bad)):
        for it in items:
            for r in recs:
                if it in r["prompt"]:
                    if not summary:
                        print(f"   {tag} {it}: [{r['timestamp'][:10]}] {r['prompt'][:200]}")
                    kinds[(tag, c["id"].split("-")[0])] += 1
print("\nby case family:", dict(kinds))
