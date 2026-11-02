"""Graded replay of the program path's reply turns only, over the ledgers of an earlier replay.

    .venv/bin/python practice/gates/replay_reply.py SRC_DIR BASE_REPLAY.json OUT.json

Every case file keeps the ledger BASE_REPLAY wrote for it, so two harness copies that differ only in how the reply
is asked (REPLY_NOTE, REWORDED_NOTE, the system prompt) can be compared without the ledger's own sampling noise.
For each case file the member that decided first decides first again, and the others read its question and reply,
as in replay_v8.py. Replies come from openai/gpt-oss-20b on the platform providers and are graded with
grade_replies (the bench grader)."""
import concurrent.futures
import json
import sys
import urllib.request
from collections import defaultdict

src, base_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, src)
sys.path.insert(0, "/home/bittensor/ditto")
sys.path.insert(0, "/home/bittensor/ditto/practice/gates/grader_probe")
from app import short  # noqa: E402
from app.answer import parse_slot  # noqa: E402
from lab.embed import api_key  # noqa: E402
from program_replies import grade  # noqa: E402

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


groups = defaultdict(list)
for m in json.load(open(base_path)):
    groups[(m["run"], m["shown"])].append(m)
print(f"{sum(map(len, groups.values()))} program questions, {len(groups)} case files, REPLY_NOTE: {short.REPLY_NOTE[:90]}...")


def replay_group(key):
    members = sorted(groups[key], key=lambda m: not m["first"])
    ledger = members[0]["ledger"]
    operator = members[0]["system_prompt"]
    earlier = None
    for m in members:
        m["base_score"], m["base_answer"] = m["new_score"], m["new_answer"]
        messages = short.program_messages(short.program_system(operator, m["question"]), m["shown"], m["question"], ledger, earlier)
        reply = chat(messages, 8000)
        m["new_final_text"], m["new_answer"] = reply, parse_slot(reply)[1] or ""
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
