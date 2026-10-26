"""List the questions of a traced run that a provider problem may have spoiled.

    .venv/bin/python tools/flag_failed_calls.py RUN_DIR [--seed S] [--size full] [--ids OUT]

Read-only. A question is flagged when one of its model calls failed (provider error, rate
limit, timeout), a call was cut at its token limit, a search pass was skipped or cut because
slow calls ate the time budget, or no answer came back. For each: its case id and category,
the reasons, whether it still answered, and its score (from report.json, or from the live
scorer's partial results while the run is going). These are the questions to re-run before
comparing two runs, so a provider hiccup is not read as a harness difference. --ids writes
the flagged canonical case ids, one per line, for tools/rerun_flagged.sh.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from lab import data  # noqa: E402
from trace_compare import plain  # noqa: E402

BUDGET_EVENT = re.compile(r"search passes .* not run: .* of the search budget left|cut at its budget")


def scores(run: Path) -> dict[str, float]:
    report = run / "report.json"
    if report.is_file():
        return {c["case_id"]: c["score"] for c in json.load(open(report))["report"]["per_case"]}
    text = (run / "scorer.log").read_text(errors="ignore")
    port = re.search(r"practice validator\) listening on :(\d+)", text)
    run_id = re.findall(r"GET /v1/runs/([0-9a-f-]+)", text)
    if not port or not run_id:
        return {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port.group(1)}/v1/runs/{run_id[-1]}", timeout=10) as resp:
            return {c["case_id"]: c["score"] for c in json.load(resp).get("partial") or []}
    except (OSError, ValueError):
        return {}


def reasons(trace: dict) -> list[str]:
    out = []
    for c in trace["calls"]:
        finish = str(c["finish"])
        if finish.startswith("llm-error") or finish == "error":
            out.append(re.sub(r"\{.*", "", finish.replace("llm-error: llm exhausted attempts: ", "failed "))[:50])
        elif finish == "length":
            out.append("cut at token limit")
    out += ["time budget: " + e[:40] for e in trace["events"] if BUDGET_EVENT.search(e)]
    if not (trace.get("final_text") or "").strip():
        out.append("no answer")
    return out


def case_of(trace: dict, by_text: dict):
    case = by_text.get(trace["user_input"])
    if case is None:
        want = plain(trace["user_input"])
        ratio, case = max(((difflib.SequenceMatcher(None, want, plain(text)).ratio(), c) for text, c in by_text.items()), key=lambda x: x[0])
        case = case if ratio >= 0.85 else None
    return case


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    ap.add_argument("--ids", type=Path, help="write the flagged canonical case ids here")
    args = ap.parse_args()
    by_text = {c.text: c for c in data.load(args.seed, 0, args.size)}
    graded = scores(args.run)
    traces = [json.loads(line) for line in open(args.run / "trace.jsonl", encoding="utf-8")]
    flagged = []
    for t in traces:
        why = reasons(t)
        if not why:
            continue
        case = case_of(t, by_text)
        cid = case.key.rsplit("/", 1)[-1] if case else "?"
        flagged.append(cid)
        print(f"{cid}  {case.phase + ':' + case.kind if case else '?':45s} score {graded.get(cid, 'pending')}  "
              f"answered {bool((t.get('final_text') or '').strip())}  lane {t.get('lane')}  | {'; '.join(sorted(set(why)))}")
    print(f"{len(flagged)} of {len(traces)} finished questions flagged")
    if "?" in flagged:
        print("some flagged questions did not match a dataset case; they are left out of --ids", file=sys.stderr)
    if args.ids:
        args.ids.write_text("".join(f"{cid}\n" for cid in flagged if cid != "?"))


if __name__ == "__main__":
    main()
