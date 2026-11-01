"""Accuracy of revert-to-middle twin members by the wording of the going-back entry (all designs), and of struck/declined cues."""
import json, re
from collections import defaultdict
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
rows = json.load(open(f"{OUT}/program_cases.json"))
calls = json.load(open(f"{OUT}/program_calls.json"))
PAT = re.compile(r"(revert|back to|previous|before the (last|most recent)|returned to)", re.I)
acc = defaultdict(lambda: defaultdict(lambda: [0, 0]))
seen_text = {}
for r in rows:
    if not r["shape"].startswith("chain:revert-to-middle") or "counterfactual" in r["relation"]:
        continue
    cl = calls.get(f"{r['run']}|{r['case_id']}")
    if not cl:
        continue
    u = "\n".join(m["content"] for m in cl[0]["messages"] if m["role"] == "user")
    sents = [s for s in re.split(r"[\n]", u) if PAT.search(s) and "no longer stands" not in s or ("back to the previous" in s)]
    cue = None
    for s in sents:
        m = re.search(r"(reverts to the previous entry instead[^\n.]*|is back to the previous entry[^\n.]*|goes back to the previous entry[^\n.]*|returned to the previous arrangement|went back to the entry before the last change|is back to what it was before the most recent change|back to the previous entry[^\n.]*)", s)
        if m:
            cue = re.sub(r"\s+", " ", m.group(1)).strip(" ;,.")
            break
    if not cue:
        cue = "?"
    fam = r["label"].split("-")[0] if not r["label"].startswith("v") else r["label"][:8]
    acc[cue]["all"][0] += r["score"] >= 1
    acc[cue]["all"][1] += 1
    acc[cue][r["shape"].split("/")[1]][0] += r["score"] >= 1
    acc[cue][r["shape"].split("/")[1]][1] += 1
for cue, d in sorted(acc.items(), key=lambda x: -x[1]["all"][1]):
    print(f"{d['all'][0]:4}/{d['all'][1]:<4} {cue[:90]:90} " + " ".join(f"{k}:{v[0]}/{v[1]}" for k, v in d.items() if k != "all"))
