"""Graded replay of a harness's program path over traced notes and questions, without running the harness.

    .venv/bin/python practice/gates/replay_v8.py SRC_DIR SOURCE_LABEL OUT.json

For every bench-14 run of SOURCE_LABEL (one per seed, the latest), each case file's notes and each program question
are taken from the traces. The program path of SRC_DIR (its ledger_messages, program_system and program_messages) is
then replayed with openai/gpt-oss-20b on the platform providers:
- one ledger per case file;
- the member that decided first in the trace decides first here;
- the other members read its question and reply.
Replies are graded with grade_replies (the bench grader). Everything is written to OUT.json: ledgers, replies,
answers and scores. The deciding call is a plain chat without tools and without the harness's final check, which
only runs when a reply has no ANSWER value."""
import concurrent.futures
import glob
import json
import re
import sys
import urllib.request
from collections import defaultdict

src, source, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, src)
sys.path.insert(0, "/home/bittensor/ditto")
sys.path.insert(0, "/home/bittensor/ditto/practice/gates/grader_probe")
from app import short  # noqa: E402
from app.answer import parse_slot  # noqa: E402
from lab.embed import api_key  # noqa: E402
from program_replies import grade, replies  # noqa: E402

PREFS = {"sort": "throughput", "ignore": ["coreweave"], "allow_fallbacks": True, "data_collection": "deny", "zdr": True}
KEY = api_key()
spent = {"prompt": 0, "completion": 0}


def chat(messages: list[dict], max_tokens: int) -> str:
    body = json.dumps({"model": "openai/gpt-oss-20b", "messages": messages, "max_tokens": max_tokens,
                       "reasoning": {"effort": "medium"}, "provider": PREFS}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.load(resp)
            usage = data.get("usage") or {}
            spent["prompt"] += usage.get("prompt_tokens", 0)
            spent["completion"] += usage.get("completion_tokens", 0)
            return (data["choices"][0]["message"].get("content") or "").strip()
        except Exception as exc:  # noqa: BLE001
            error = exc
    return f"(failed: {error})"


def latest_runs() -> dict[int, str]:
    runs = {}
    for run in sorted(glob.glob(f"/home/bittensor/ditto/practice/2026*_ditto-harness-{source}_full*")):
        try:
            rep = json.load(open(f"{run}/report.json"))
        except OSError:
            continue
        runs[int(rep["seed"])] = run
    return runs


def traced_inputs(run: str) -> dict[str, dict]:
    """Per program question of a run: the served question, operator prompt, shown notes, the notes as the ledger
    reads them, and whether it decided first."""
    out = {}
    for line in open(f"{run}/trace.jsonl"):
        t = json.loads(line)
        if t.get("path") != "program":
            continue
        first_user = next((c["messages"][1]["content"] for c in t["calls"] if len(c["messages"]) > 2 and c["messages"][1]["role"] == "user"
                           and "\n\nMessage:\n" in c["messages"][1]["content"]), None)
        ledger_view = next((c["messages"][1]["content"].split("\n\nThese are the case file's entries")[0] for c in t["calls"]
                            if "These are the case file's entries" in c["messages"][1]["content"]), None)
        if first_user is None:
            continue
        out[t["user_input"]] = {"system_prompt": t.get("system_prompt") or "", "shown": first_user.split("\n\nMessage:\n")[0],
                                "ledger_view": ledger_view, "first": "earlier reply: from" not in " ".join(t.get("events") or [])}
    return out


rows = [r for r in replies([source]) if r["run"] in set(latest_runs().values())]
inputs = {run: traced_inputs(run) for run in latest_runs().values()}
groups = defaultdict(list)
for r in rows:
    got = inputs[r["run"]].get(r["question"])
    if got is None:
        continue
    r.update(got)
    groups[(r["run"], r["shown"])].append(r)
ledger_views = {}
for key, members in groups.items():
    ledger_views[key] = next((m["ledger_view"] for m in members if m["ledger_view"]), None)
print(f"{len(rows)} program questions, {len(groups)} case files over {len(latest_runs())} seeds")


def replay_group(key):
    members = sorted(groups[key], key=lambda m: not m["first"])
    view = ledger_views[key]
    operator = members[0]["system_prompt"]
    ledger = chat(short.ledger_messages(operator, view), short.LEDGER_MAX_TOKENS) if view else None
    earlier = None
    for m in members:
        messages = short.program_messages(short.program_system(operator, m["question"]), m["shown"], m["question"], ledger, earlier)
        reply = chat(messages, 8000)
        m["ledger"], m["new_final_text"], m["new_answer"] = ledger, reply, parse_slot(reply)[1] or ""
        if earlier is None and m["new_answer"]:
            earlier = (m["question"], reply)
    return members


with concurrent.futures.ThreadPoolExecutor(8) as pool:
    done = [m for members in pool.map(replay_group, list(groups)) for m in members]
graded = grade([{"seed": m["seed"], "id": m["id"], "answer": m["new_answer"], "final_text": m["new_final_text"]} for m in done])
for m, g in zip(done, graded):
    m["new_score"], m["new_notes"] = g["score"], g["notes"]
json.dump(done, open(out_path, "w"), indent=1)
cost = spent["prompt"] * 0.03e-6 + spent["completion"] * 0.15e-6
print(f"tokens prompt {spent['prompt']} completion {spent['completion']} (about ${cost:.2f}); written {out_path}")
