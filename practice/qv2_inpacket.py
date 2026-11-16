"""querverweis: for each missed item and named trap, is each of its records in what the model read (any call's
messages)? Split by how the record names the person: full name, title+surname, first name only, other.

    python3 practice/qv2_inpacket.py RUN_DIR PACK_RUN AGENT
"""
import json, re, sys, collections
run, pr, agent = sys.argv[1:4]
pack = json.load(open(f"{run}/packs/{pr.rsplit('-r', 1)[0]}.json"))
recs = [x for w in pack["memory_waves"] for x in w["pairs"]]
byq = {c["question"]: c for c in pack["cases"]}
norm = lambda s: " ".join(s.lower().split())
hit = lambda text, phrase: re.search(r"(?<![a-z0-9])" + re.escape(norm(phrase)) + r"(?![a-z0-9])", text) is not None
tally = collections.Counter()
for line in open(f"{run}/trace/{pr}/{agent}/trace.jsonl"):
    t = json.loads(line)
    c = byq[t["user_input"]]
    seen = ""
    for call in t.get("calls") or []:
        for m in call.get("messages") or call.get("request", {}).get("messages") or []:
            seen += m["content"] if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
    m = re.search(r"does ((?:[A-Z][\w'-]+ )+)(?:get|buy|swim|climb|watch|work|go|eat|see|play|take)", c["question"])
    full = m.group(1).strip() if m else ""
    first, last = (full.split()[0], full.split()[-1]) if full else ("", "")
    reply = norm(t.get("final_text") or "")
    for tag, items in (("missed", [i for i in c["answer_items"] if not hit(reply, i)]), ("trap", [x for x in c["distractor_answers"] if hit(reply, x)])):
        for it in items:
            for r in recs:
                if it not in r["prompt"]:
                    continue
                p = r["prompt"]
                how = "full" if full and full in p else "title" if last and re.search(r"\b(?:Mr|Ms|Mrs|Dr)\. " + last, p) else "first" if first and re.search(r"\b" + first + r"\b", p) else "other"
                tally[(tag, how, "in packet" if p.strip()[:60] in seen else "NOT in packet")] += 1
for k, v in sorted(tally.items()):
    print(k, v)
