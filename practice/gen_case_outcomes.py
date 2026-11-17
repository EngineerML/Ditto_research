"""Per case: scorer status and mean, and per agent how many items it named and whether it named a distractor
(I = items named, T = trap named, 0 = declined / none). Then, for each status, how often agents named all items,
some items, or a trap.
    python3 practice/gen_case_outcomes.py RUN_DIR [FAMILY_SUBSTRING]
"""
import json, os, re, sys, glob, collections
run = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 else ""
norm = lambda s: " ".join(s.lower().replace(" ", " ").split())
hit = lambda text, phrase: re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None
summary = collections.defaultdict(collections.Counter)
for rf in sorted(glob.glob(f"{run}/run-*.json")):
    seed = rf.rsplit("/", 1)[1][4:-5]          # seed-1-r0
    pack = json.load(open(f"{run}/packs/{seed.rsplit('-r', 1)[0]}.json"))
    scored = [c for s in json.load(open(rf))["score"]["seeds"] for c in s["cases"]]   # same order as the pack
    status = {}
    replies = collections.defaultdict(dict)
    for agent in sorted(os.listdir(f"{run}/trace/{seed}")):
        p = f"{run}/trace/{seed}/{agent}/trace.jsonl"
        if os.path.exists(p):
            for line in open(p):
                t = json.loads(line)
                replies[t["user_input"]][agent] = norm(t.get("final_text") or "")
    for c, st in zip(pack["cases"], scored):
        cid = st["case_id"]
        if want not in cid:
            continue
        row = []
        for agent, r in sorted(replies[c["question"]].items()):
            n = sum(hit(r, i) for i in c["answer_items"])
            trap = any(hit(r, x) for x in c["distractor_answers"])
            tag = "T" if trap else f"{n}/{len(c['answer_items'])}"
            row.append(f"{agent}:{tag}")
            summary[st["status"]]["trap" if trap else "all" if n == len(c["answer_items"]) else "some" if n else "none"] += 1
        print(f"{cid:34s} {st['status'][:5]:5s} mean {st['mean_score']:.2f}  " + "  ".join(row))
print()
for k, v in summary.items():
    print(f"{k:15s} agent outcomes: " + "  ".join(f"{x} {v[x]}" for x in ("all", "some", "none", "trap")))
