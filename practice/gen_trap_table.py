"""Generator calibration: per agent, which items each link yields and which distractors get named, by link kind.
Each item / trap is attributed to its link by the records that write it (session relay, number receipt, title,
given-up, role, name shape, full name).

    python3 practice/gen_trap_table.py RUN_DIR
"""
import json, os, re, sys, collections
run = sys.argv[1]
norm = lambda s: " ".join(s.lower().split())
hit = lambda text, phrase: re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None


def link_of(text):
    t = text.lower()
    if "depends on" in t:
        return "cond"
    if any(w in t for w in ("turned it down", "decided against", "didn't go back", "stopped bothering")):
        return "intent"
    if "membership" in t or "receipt" in t or "membesrhip" in t:
        return "number"
    if re.search(r"\b(ms|mr)\. ", t):
        return "title"
    if any(w in t for w in ("lapse", "enough of", "never to set foot", "instead", "these days", "has a loyalty card", "goes to", "stopped going", "given up on", "since leaving")):
        return "givenup"
    if " lead " in t:
        return "role"
    if re.match(r"^(my |the (person|friend|volunteer|parent))", t) or "swears by" in t and not re.search(r"[A-Z][a-z]+ [A-Z]", text[:30]):
        return "session"
    return "full/shape"


got = collections.Counter()
missed = collections.Counter()
named = collections.Counter()
for pr in sorted(os.listdir(f"{run}/trace")):
    pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
    recs = [x["prompt"] for w in pack["memory_waves"] for x in w["pairs"]]
    byq = {c["question"]: c for c in pack["cases"]}
    for agent in sorted(os.listdir(f"{run}/trace/{pr}")):
        path = f"{run}/trace/{pr}/{agent}/trace.jsonl"
        if not os.path.exists(path):
            continue
        for line in open(path):
            t = json.loads(line)
            c = byq[t["user_input"]]
            reply = norm(t.get("final_text") or "")
            for item in c["answer_items"]:
                kind = next((link_of(r) for r in recs if item in r), "?")
                (got if hit(reply, item) else missed)[(agent, kind)] += 1
            for trap in c["distractor_answers"]:
                if hit(reply, trap):
                    kinds = sorted({link_of(r) for r in recs if trap in r})
                    named[(agent, "+".join(kinds))] += 1
agents = sorted({a for a, _ in got} | {a for a, _ in missed})
kinds = sorted({k for _, k in got} | {k for _, k in missed})
print("item found / total by link")
for k in kinds:
    print(" ", k.ljust(12), "  ".join(f"{a} {got[(a, k)]}/{got[(a, k)] + missed[(a, k)]}" for a in agents))
print("distractors named, by the links of their records")
for (a, k), v in sorted(named.items()):
    print(" ", a, k, v)
