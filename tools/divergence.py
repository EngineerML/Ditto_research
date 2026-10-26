"""Why two traced runs scored a question differently: routing, selection, or the model's own sampling.

    .venv/bin/python tools/divergence.py OUT.md A=RUN B=RUN [--seed S] [--size full] [--all]

For each question the runs score differently (--all: every question), walk both trajectories
call by call. The first call whose prompt differs, or whose reply differs while the prompt was
the same, names the cause:
- routing: the lanes differ;
- sampling: every prompt up to the first different reply was byte-identical, so the same model
  on the same input chose differently (no fixed seed, provider sampling); when that reply is
  the recall turn's memory queries, the records that follow differ too;
- selection: the first different prompt carries different records;
- prompt: the first different prompt carries the same records (another step's output differs).
The table gives, per cause, how many questions each run won.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from flag_failed_calls import case_ids, latencies  # noqa: E402
from lab import data  # noqa: E402


def prompt(call: dict) -> str:
    return json.dumps([call["messages"], call["tools"], call["settings"]], sort_keys=True)


def first_split(a: dict, b: dict) -> tuple[str, int]:
    """(how the two trajectories first part, at which call)."""
    for i, (x, y) in enumerate(zip(a["calls"], b["calls"])):
        if prompt(x) != prompt(y):
            return "prompt", i
        if (x.get("reply"), json.dumps(x.get("tool_calls"))) != (y.get("reply"), json.dumps(y.get("tool_calls"))):
            return "reply", i
    return ("length" if len(a["calls"]) != len(b["calls"]) else "same"), min(len(a["calls"]), len(b["calls"]))


def records(trace: dict) -> list[str]:
    return [p[1] for p in trace.get("packet") or [] if p and len(p) > 1]


def cause(a: dict, b: dict) -> tuple[str, str]:
    if a.get("lane") != b.get("lane"):
        return "routing", f"{a.get('lane')} vs {b.get('lane')}"
    sa, sb = set(records(a)), set(records(b))
    packets = "" if records(a) == records(b) else "same records, other order" if sa == sb else f"{len(sa - sb)} records only in A, {len(sb - sa)} only in B"
    how, at = first_split(a, b)
    if how == "reply":
        # the recall turn that picks memory queries comes before the packet, so a sampled
        # difference there also shows up as different records
        return "sampling", f"same prompts, replies part at call {at}" + (f"; then {packets}" if packets else "")
    if how == "prompt":
        return ("selection", f"prompts part at call {at}: {packets}") if packets else ("prompt", f"prompts part at call {at}")
    return "sampling", f"identical calls ({how})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("runs", nargs=2)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    by_id = {c.key.rsplit("/", 1)[-1]: c for c in cases}
    runs = []
    for spec in args.runs:
        label, path = spec.split("=", 1)
        run = Path(path)
        rows = {c["case_id"]: c for c in json.load(open(run / "report.json"))["report"]["per_case"]}
        traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
        runs.append((label, rows, dict(zip(case_ids(traces, cases, latencies(list(rows.values()))), traces))))
    (la, ra, ta), (lb, rb, tb) = runs
    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    lines = []
    for cid, case in by_id.items():
        sa, sb = ra.get(cid, {}).get("score"), rb.get(cid, {}).get("score")
        if sa is None or sb is None or cid not in ta or cid not in tb or (sa == sb and not args.all):
            continue
        why, detail = cause(ta[cid], tb[cid])
        winner = la if sa > sb else lb if sb > sa else "tie"
        tally[why][winner] += 1
        lines.append(f"| {cid} | {case.phase}:{case.kind} | {sa:.3g} | {sb:.3g} | {why} | {detail} |")
    out = [f"# Where {la} and {lb} part", "", f"| cause | {la} better | {lb} better | tie |", "|---|---|---|---|"]
    out += [f"| {why} | {c[la]} | {c[lb]} | {c['tie']} |" for why, c in sorted(tally.items())]
    out += ["", f"| case | category | {la} | {lb} | cause | detail |", "|---|---|---|---|---|---|"] + sorted(lines, key=lambda l: l.split("|")[5])
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:4 + len(tally)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
