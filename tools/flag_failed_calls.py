"""List the questions of a traced run that a provider problem may have spoiled.

    .venv/bin/python tools/flag_failed_calls.py RUN_DIR [--seed S] [--size full] [--ids OUT] [--missing]

Read-only. A question is flagged when one of its model calls failed (provider error, rate
limit, timeout), a call was cut at its token limit, a search pass was skipped or cut because
slow calls ate the time budget, or no answer came back. For each: its case id and category,
the reasons, whether it still answered, and its score (from report.json, a saved
scorer_status.json, or the live scorer's partial results while the run is going). These are the questions to re-run before
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

LATENCY_SLACK = 0.5  # seconds between the scorer's latency and the trace's duration
BUDGET_EVENT = re.compile(r"search passes .* not run: .* of the search budget left|cut at its budget")


def graded_rows(run: Path) -> list[dict]:
    """Per-case results: report.json, else a saved scorer_status.json, else the live scorer's partial results."""
    if (run / "report.json").is_file():
        return json.load(open(run / "report.json"))["report"]["per_case"]
    if (run / "scorer_status.json").is_file():
        return json.load(open(run / "scorer_status.json")).get("partial") or []
    text = (run / "scorer.log").read_text(errors="ignore")
    port = re.search(r"practice validator\) listening on :(\d+)", text)
    run_id = re.findall(r"GET /v1/runs/([0-9a-f-]+)", text)
    if not port or not run_id:
        return []
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port.group(1)}/v1/runs/{run_id[-1]}", timeout=10) as resp:
            return json.load(resp).get("partial") or []
    except (OSError, ValueError):
        return []


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


def case_ids(traces: list[dict], cases: list, latency: dict[str, float]) -> list[str]:
    """The canonical case id of each trace ("?" when none fits), one trace per case.

    The scorer's latency for a case and the trace's own duration agree to about 10 ms, so a case
    graded within LATENCY_SLACK of the trace's duration and with loosely similar text is the
    first choice (twins whose text the harness sees identically are told apart this way; some
    cases reach the harness reworded). Otherwise the closest text decides, at least 0.85
    similar. Each case takes one trace.
    """
    ids = {c.key.rsplit("/", 1)[-1]: plain(c.text) for c in cases}
    options = []
    for i, trace in enumerate(traces):
        want = plain(trace["user_input"])
        for cid, text in ids.items():
            gap = abs((trace.get("seconds") or 0) - latency[cid]) if cid in latency else None
            close = gap is not None and gap <= LATENCY_SLACK
            matcher = difflib.SequenceMatcher(None, want, text)
            if not close and matcher.quick_ratio() < 0.85:
                continue
            ratio = matcher.ratio()
            if close and ratio >= 0.3:
                options.append((0, ratio < 0.85, gap, i, cid))
            elif ratio >= 0.85:  # never graded, or latency off: closest text, then nearest latency
                options.append((1 if gap is None else 2, -ratio, gap or 0, i, cid))
    out, taken = ["?"] * len(traces), set()
    for *_, i, cid in sorted(options):
        if out[i] == "?" and cid not in taken:
            out[i] = cid
            taken.add(cid)
    return out


def latencies(rows: list[dict]) -> dict[str, float]:
    return {c["case_id"]: (c.get("latency_ms") or 0) / 1000 for c in rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    ap.add_argument("--ids", type=Path, help="write the flagged canonical case ids here")
    ap.add_argument("--missing", action="store_true", help="also flag questions with no trace (a run cut short)")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    by_id = {c.key.rsplit("/", 1)[-1]: c for c in cases}
    rows = graded_rows(args.run)
    graded = {c["case_id"]: c["score"] for c in rows}
    traces = [json.loads(line) for line in open(args.run / "trace.jsonl", encoding="utf-8")]
    ids = case_ids(traces, cases, latencies(rows))
    flagged = []
    for t, cid in zip(traces, ids):
        why = reasons(t)
        if not why:
            continue
        case = by_id.get(cid)
        flagged.append(cid)
        print(f"{cid}  {case.phase + ':' + case.kind if case else '?':45s} score {graded.get(cid, 'pending')}  "
              f"answered {bool((t.get('final_text') or '').strip())}  lane {t.get('lane')}  | {'; '.join(sorted(set(why)))}")
    print(f"{len(flagged)} of {len(traces)} finished questions flagged")
    if "?" in ids:
        print(f"{ids.count('?')} traces did not match a dataset case", file=sys.stderr)
    if args.missing:
        unanswered = sorted(set(by_id) - (set(ids) & set(graded)))
        print(f"{len(unanswered)} questions have no trace or no grade (the run stopped before them)")
        flagged += unanswered
    if args.ids:
        args.ids.write_text("".join(f"{cid}\n" for cid in dict.fromkeys(flagged) if cid != "?"))


if __name__ == "__main__":
    main()
