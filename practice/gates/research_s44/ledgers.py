"""ledgers.py SEED DOMAIN GROUP [grep] : print every ledger / shared-draft reply (first call written here) for the group, filtered to lines matching grep."""
import json, sys, re
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
rows = json.load(open(f"{OUT}/program_cases.json"))
calls = json.load(open(f"{OUT}/program_calls.json"))
seed, dom, grp = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
pat = re.compile(sys.argv[4].replace("/", "|"), re.I) if len(sys.argv) > 4 else None
for r in sorted([r for r in rows if r["seed"] == seed and r["domain"] == dom and r["group"] == grp], key=lambda r: (r["run"], r["relation"])):
    cl = calls.get(f"{r['run']}|{r['case_id']}") or []
    for i, c in enumerate(cl):
        sysm = next((m["content"] for m in c["messages"] if m["role"] == "system"), "")
        if len(c["messages"]) == 2 and ("ledger" in sysm.lower() or i == 0 and len(cl) > 1):
            rep = c["reply"] or ""
            lines = [l for l in rep.splitlines() if (pat is None or pat.search(l))]
            print(f"{r['label']} {r['run'][9:15]} {r['relation'][:4]} score={r['score']} call{i}: " + " || ".join(l.strip() for l in lines)[:1200])

