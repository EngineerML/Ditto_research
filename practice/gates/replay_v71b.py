"""Replay v7.1's program-path prompts over the first replies traced in the v7-prog2 s44 runs.

For each case file (scope) the ledger is rewritten with v7.1's LEDGER_BRIEF from the same notes; for each first
reply the deciding call is re-sent with v7.1's LEDGER_ASK, the new ledger and v7.1's REPLY_NOTE. Answers are checked
against the dataset's expected answer with a loose matcher (case, punctuation and list separators ignored); the
matcher is first calibrated on the traced answers against the real grader's scores. Args: V7_SRC_DIR."""
import concurrent.futures
import difflib
import glob
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, "/home/bittensor/ditto")
sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
from app import short  # noqa: E402
from lab.embed import api_key  # noqa: E402
from v14_oracle import shapes  # noqa: E402

PREFS = {"sort": "throughput", "ignore": ["coreweave"], "allow_fallbacks": True, "data_collection": "deny", "zdr": True}
SCOPE_RE = re.compile(r"\bc[0-9a-f]{16}\b")
PROGRAM = ("v13-open-program", "v13-personal-program")
KEY = api_key()


def chat(messages, max_tokens):
    body = json.dumps({"model": "openai/gpt-oss-20b", "messages": messages, "max_tokens": max_tokens,
                       "reasoning": {"effort": "medium"}, "provider": PREFS}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.load(resp)["choices"][0]["message"].get("content") or ""
        except Exception as exc:  # noqa: BLE001
            err = exc
    return f"(failed: {err})"


def answer(text):
    found = re.findall(r"ANSWER:\s*(.+)", text or "")
    return found[-1].strip() if found else ""


def items(text):
    text = (text or "").lower().replace(" ", " ").replace("‑", "-")
    parts = re.split(r"\s*[;,]\s*|\s+[–—-]\s+|\s+and\s+", text)
    return sorted(p for p in (re.sub(r"\s+", " ", re.sub(r"^[\W_]+|[\W_]+$", "", x)).strip() for x in parts) if p)


def right(got, expected):
    return bool(got) and items(got) == items(expected)


jobs = []
for run in sorted(glob.glob("/home/bittensor/ditto/practice/20261101T1*_ditto-harness-v7-prog2_full_rerun")):
    rep = json.load(open(f"{run}/report.json"))
    seed = int(rep["seed"])
    oracle = shapes(seed)
    data = json.load(open(f"/home/bittensor/ditto/.cache/datasets/v14_s{seed}_salt0_full.json"))
    known = [c for c in data["memory_cases"] if c["question_type"] in PROGRAM]
    scores = {c["case_id"].rsplit("/", 1)[-1]: c["score"] for c in rep["report"]["per_case"]}
    traces = [json.loads(line) for line in open(f"{run}/trace.jsonl")]
    ledgers = {}
    for t in traces:
        for call in t.get("calls") or []:
            content = call["messages"][1]["content"] if len(call["messages"]) > 1 else ""
            if call["messages"][0]["content"].startswith(short.LEDGER_SYSTEM) and "These are the case file's entries" in content:
                ledgers[content.split("\n\nThese are the case file's entries")[0]] = call["messages"]
    for t in traces:
        if t.get("path") != "program" or "earlier reply: from" in " ".join(t.get("events") or []):
            continue
        deciding = next((c for c in t["calls"] if [m["role"] for m in c["messages"]] == ["system", "user", "assistant", "user"]), None)
        scope = SCOPE_RE.search(t["user_input"])
        case = max((c for c in known if scope and scope.group(0) in c["question"]),
                   key=lambda c: difflib.SequenceMatcher(None, c["question"], t["user_input"]).ratio(), default=None)
        if deciding is None or case is None:
            continue
        first_user = deciding["messages"][1]["content"]
        notes = next((n for n in ledgers if n in first_user), None)
        if notes is None:
            continue
        jobs.append({"seed": seed, "label": oracle[case["id"]].label, "relation": oracle[case["id"]].relation,
                     "expected": case["expected_answer"], "old": t.get("answer") or answer(t.get("final_text")),
                     "graded": scores.get(case["id"]), "notes": notes, "ledger_messages": ledgers[notes],
                     "deciding": deciding["messages"]})
PREV = json.load(open("/home/bittensor/ditto/practice/gates/s44/replay_v71.json"))
assert len(PREV) == len(jobs)
jobs = [j for j, p in zip(jobs, PREV) if items(p["new"]) != items(p["old"])]
print(len(jobs), "first replies,", len({j['notes'] for j in jobs}), "case files")
agree = sum(1 for j in jobs if j["graded"] is not None and right(j["old"], j["expected"]) == (j["graded"] >= 1))
print(f"matcher agrees with the grader on {agree}/{len(jobs)} traced answers")

new_ledger = {}


def ledger_for(notes):
    msgs = jobs_by_notes[notes]["ledger_messages"]
    return chat([msgs[0], {"role": "user", "content": short.LEDGER_BRIEF.format(notes=notes)}], short.LEDGER_MAX_TOKENS).strip()


jobs_by_notes = {j["notes"]: j for j in jobs}
with concurrent.futures.ThreadPoolExecutor(8) as pool:
    for notes, text in zip(jobs_by_notes, pool.map(ledger_for, jobs_by_notes)):
        new_ledger[notes] = text


def decide(job):
    msgs = job["deciding"]
    first = msgs[1]["content"].split("\n\nBefore replying, write the ledger")[0] + "\n\n" + short.LEDGER_ASK
    return chat([msgs[0], {"role": "user", "content": first}, {"role": "assistant", "content": new_ledger[job["notes"]]},
                 {"role": "user", "content": short.REPLY_NOTE}], 8000)


with concurrent.futures.ThreadPoolExecutor(8) as pool:
    replies = list(pool.map(decide, jobs))
by_shape = defaultdict(lambda: [0, 0, 0])
echo = 0
for job, reply in zip(jobs, replies):
    job["new"] = answer(reply)
    echo += bool(re.search(r"^\s*(\[M\d+\]|NOW )", reply, re.M))
    old_ok, new_ok = (job["graded"] or 0) >= 1, right(job["new"], job["expected"])
    cell = by_shape[job["label"]]
    cell[0] += old_ok
    cell[1] += new_ok
    cell[2] += 1
    if old_ok != new_ok:
        print(f"{'FIXED' if new_ok else 'LOST '} {job['label'][:34]:34} {job['relation'][:12]:12} exp={job['expected'][:50]!r} old={job['old'][:50]!r} new={job['new'][:50]!r}")
print(f"\n{'shape':40} graded-old  new(matcher) of n")
for label, (o, n, total) in sorted(by_shape.items()):
    print(f"{label:40} {o:6}  {n:6}  {total:4}")
print("total", sum(c[0] for c in by_shape.values()), "->", sum(c[1] for c in by_shape.values()), "of", len(jobs), "| replies repeating the ledger:", echo)
json.dump([{k: v for k, v in j.items() if k not in ("ledger_messages", "deciding", "notes")} for j in jobs],
          open("/home/bittensor/ditto/practice/gates/s44/replay_v71b.json", "w"), indent=1)
json.dump(new_ledger, open("/home/bittensor/ditto/practice/gates/s44/replay_v71b_ledgers.json", "w"), indent=1)
print("\nnew answer vs old answer (same items = unchanged):")
for job in jobs:
    same = items(job["new"]) == items(job["old"])
    print(f"{'same ' if same else 'DIFF '} {'ok' if right(job['new'], job['expected']) else '  '} {job['label'][:30]:30} exp={job['expected'][:40]!r} old={job['old'][:40]!r} new={job['new'][:45]!r}")
