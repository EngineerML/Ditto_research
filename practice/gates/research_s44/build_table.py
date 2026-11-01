"""Per-case table of program questions over every bench-14 run with a report, joined to traces and oracle shapes."""
import csv
import difflib
import glob
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
from v14_oracle import shapes  # noqa

ROOT = "/home/bittensor/ditto"
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
PROGRAM = ("v13-open-program", "v13-personal-program")
SCOPE_RE = re.compile(r"\bc[0-9a-f]{16}\b")


def label(run):
    m = re.search(r"ditto-harness-(.+?)_full", run)
    return m.group(1) if m else run


def norm_calls(t):
    out = []
    for c in t.get("calls") or []:
        msgs = c.get("messages") or []
        out.append({
            "messages": [{"role": m.get("role"), "content": m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))} for m in msgs],
            "reply": c.get("reply"),
            "settings": c.get("settings"),
        })
    return out


def notes_hash(t):
    """Hash of the notes the deciding call saw: the first user turn up to 'Message:' of the last call."""
    calls = t.get("calls") or []
    for c in reversed(calls):
        for m in c.get("messages") or []:
            if m.get("role") == "user":
                txt = m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
                cut = txt.find("\nMessage:")
                body = txt[:cut] if cut >= 0 else txt
                return hashlib.sha1(body.encode()).hexdigest()[:10], len(body)
    return "", 0


def main():
    rows = []
    dumps = {}
    datasets = {}
    for d in sorted(glob.glob(f"{ROOT}/practice/2026*_ditto-harness-*")):
        try:
            rep = json.load(open(f"{d}/report.json"))
        except Exception:
            continue
        if rep.get("bench_version") != 14:
            continue
        body = rep.get("report") if isinstance(rep.get("report"), dict) else {}
        cases = [c for c in (body.get("per_case") or rep.get("partial") or []) if c.get("category") in PROGRAM]
        if not cases:
            continue
        seed = rep.get("seed")
        if seed not in datasets:
            p = f"{ROOT}/.cache/datasets/v14_s{seed}_salt0_full.json"
            data = json.load(open(p)) if os.path.exists(p) else {"memory_cases": []}
            datasets[seed] = {c["id"]: c for c in data["memory_cases"] if c["question_type"] in PROGRAM}
        known = datasets[seed]
        oracle = shapes(seed)
        by_scope = defaultdict(list)
        if os.path.exists(f"{d}/trace.jsonl"):
            with open(f"{d}/trace.jsonl") as f:
                for line in f:
                    try:
                        t = json.loads(line)
                    except ValueError:
                        continue
                    m = SCOPE_RE.search(t.get("user_input") or "")
                    if m:
                        by_scope[m.group(0)].append(t)
        run = os.path.basename(d)
        for c in cases:
            cid = c.get("case_id")
            case = known.get(cid)
            sh = oracle.get(cid)
            q = case["question"] if case else ""
            t = {}
            if case:
                m = SCOPE_RE.search(q)
                found = by_scope.get(m.group(0), []) if m else []
                if found:
                    t = max(found, key=lambda x: difflib.SequenceMatcher(None, x["user_input"], q).ratio())
            ev = t.get("events") or []
            if isinstance(ev, str):
                ev = [ev]
            nh, nlen = notes_hash(t) if t else ("", 0)
            row = {
                "run": run, "label": label(run), "seed": seed, "case_id": cid,
                "category": c.get("category"), "relation": c.get("relation") or (sh.relation if sh else None),
                "twin_group": c.get("twin_group"),
                "shape": sh.label if sh else None, "domain": sh.domain if sh else None, "group": sh.group if sh else None,
                "score": c.get("score") or 0, "grader_notes": c.get("notes"),
                "question": t.get("user_input") or q, "expected": case.get("expected_answer") if case else None,
                "accept_any": case.get("accept_any") if case else None,
                "distractor_answers": case.get("distractor_answers") if case else None,
                "answer": t.get("answer"), "final_text": t.get("final_text"),
                "path": t.get("path"), "lane": t.get("lane"), "events": ev,
                "model_calls": t.get("model_calls"), "n_calls": len(t.get("calls") or []),
                "notes_hash": nh, "notes_len": nlen, "traced": bool(t),
                "decided_first": None,
            }
            evs = " | ".join(map(str, ev))
            if "written for an earlier rewording" in evs or "earlier reply: from an earlier" in evs:
                row["decided_first"] = False
            elif "shared draft: written here" in evs or "ledger" in evs or "shared draft" in evs:
                row["decided_first"] = True
            rows.append(row)
            if t:
                dumps[f"{run}|{cid}"] = norm_calls(t)
    json.dump(rows, open(f"{OUT}/program_cases.json", "w"), indent=0)
    with open(f"{OUT}/program_cases.csv", "w", newline="") as f:
        cols = ["label", "seed", "run", "case_id", "shape", "domain", "group", "relation", "score", "decided_first", "notes_hash", "answer", "expected", "events"]
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[k] if k != "events" else " | ".join(map(str, r[k])) for k in cols])
    json.dump(dumps, open(f"{OUT}/program_calls.json", "w"))
    print(len(rows), "rows", sum(r["traced"] for r in rows), "traced", sum(r["shape"] is not None for r in rows), "shaped")


main()
