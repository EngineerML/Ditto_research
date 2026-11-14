import json, glob, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.tracked import already_tracked, unlisted_create
from app.jobs import running_job
from dataclasses import dataclass


@dataclass
class R:
    name: str
    output: str
    state: str = "completed"


runs = sys.argv[1:] or sorted(glob.glob("/home/bittensor/ditto/practice/2026111*_ditto-harness-*_full_rerun")) + sorted(glob.glob("/home/bittensor/ditto/practice/2026111*_full"))
total = holds = 0
for run in runs:
    for f in glob.glob(run + "/**/trace.jsonl", recursive=True):
        for line in open(f):
            t = json.loads(line)
            if not t.get("calls"):
                continue
            history = max((c["messages"] for c in t["calls"]), key=len)
            ledger, names, fired = [], {}, []
            for m in history:
                if m.get("role") == "assistant" and m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        name = (tc.get("function") or {}).get("name") or ""
                        for kind, hit in (("TRACKED", already_tracked(name, t["user_input"], ledger, "completed")),
                                          ("UNLISTED", unlisted_create(name, t["user_input"], ledger, "completed")),
                                          ("JOB", running_job(name, t["user_input"], ledger, "completed"))):
                            if hit:
                                fired.append((name, kind))
                        names[tc.get("id")] = name
                elif m.get("role") == "tool":
                    ledger.append(R(names.get(m.get("tool_call_id"), "?"), str(m.get("content"))))
            total += 1
            if fired:
                holds += 1
                print(run.split("/")[-1][:30], "|", t["user_input"][:70], "->", fired)
print("cases", total, "with a hold", holds)
