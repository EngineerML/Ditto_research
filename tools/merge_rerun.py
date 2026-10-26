"""Merge a re-run of flagged questions back into its full practice run.

    .venv/bin/python tools/merge_rerun.py FULL_RUN RERUN_RUN OUT_DIR [--seed S] [--size full]

For each case id in RERUN_RUN/only_cases.txt, the full run's per-case score and trace row are
replaced by the re-run's (cases the scorer only ran as a run-after dependency are not taken).
The merged per-case scores are re-aggregated with the official scorer (.cache/ditto-rescore),
so composite, means and gate factors are the numbers the full run would have reported with
those answers. OUT_DIR gets report.json and trace.jsonl in the usual layout (for
tools/compare_agents.py), replaced.jsonl with the original rows, and rerun.md listing each
question's old and new score and whether the re-run itself still hit a provider problem.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from flag_failed_calls import case_of, reasons  # noqa: E402
from lab import data  # noqa: E402

RESCORE = HERE / ".cache" / "ditto-rescore"
GATE_KEYS = ("tool_efficiency", "metamorphic_consistency", "conversational_sanity", "memory_over_call")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("full", type=Path)
    ap.add_argument("rerun", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    args = ap.parse_args()
    wanted = (args.rerun / "only_cases.txt").read_text().split()
    by_text = {c.text: c for c in data.load(args.seed, 0, args.size)}

    def cid_of(trace: dict) -> str:
        case = case_of(trace, by_text)
        return case.key.rsplit("/", 1)[-1] if case else "?"

    full = json.load(open(args.full / "report.json"))
    redo = {c["case_id"]: c for c in json.load(open(args.rerun / "report.json"))["report"]["per_case"]}
    redo_traces = {cid_of(t): t for t in map(json.loads, open(args.rerun / "trace.jsonl", encoding="utf-8"))}
    missing = [cid for cid in wanted if cid not in redo or cid not in redo_traces]
    if missing:
        print(f"re-run lacks {len(missing)} of the listed cases: {' '.join(missing)}", file=sys.stderr)
        return 1

    before = {}
    per_case = []
    for row in full["report"]["per_case"]:
        if row["case_id"] in wanted:
            before[row["case_id"]] = row
            row = dict(redo[row["case_id"]], rerun_of_score=row["score"])
        per_case.append(row)
    full["report"]["per_case"] = per_case

    args.out.mkdir(parents=True, exist_ok=True)
    merged_rows, replaced = [], []
    for trace in map(json.loads, open(args.full / "trace.jsonl", encoding="utf-8")):
        cid = cid_of(trace)
        if cid in wanted:
            replaced.append(trace)
            trace = dict(redo_traces[cid], rerun=True)
        merged_rows.append(trace)
    (args.out / "trace.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in merged_rows), encoding="utf-8")
    (args.out / "replaced.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in replaced), encoding="utf-8")

    (args.out / "report.json").write_text(json.dumps(full))
    rescored = json.loads(subprocess.run([str(RESCORE), str(args.out / "report.json")], capture_output=True, text=True, check=True).stdout)
    report = full["report"]
    old = {k: report[k] for k in ("composite", "tool_mean", "memory_mean")} | {k: report["details"].get(k) for k in GATE_KEYS}
    for key in ("composite", "raw_composite", "tool_mean", "memory_mean", "conversational_sanity"):
        if key in rescored["report"]:
            report[key] = rescored["report"][key]
    report["details"].update({k: v for k, v in rescored["gates"].items()})
    report["details"]["tool_mean"], report["details"]["memory_mean"] = report["tool_mean"], report["memory_mean"]
    report["merged_rerun"] = {"from": str(args.rerun), "cases": wanted, "before": old}
    (args.out / "report.json").write_text(json.dumps(full))

    lines = [f"# Re-run merged into {args.full.name}", "", f"re-run: {args.rerun.name}", "",
             "| | before | after |", "|---|---|---|"]
    lines += [f"| {k} | {old[k]} | {report[k] if k in report else report['details'].get(k)} |" for k in old]
    lines += ["", "| case | category | score before | after | re-run still hit |", "|---|---|---|---|---|"]
    for cid in wanted:
        still = "; ".join(sorted(set(reasons(redo_traces[cid])))) or "-"
        lines.append(f"| {cid} | {before[cid]['category']} | {before[cid]['score']:.3g} | {redo[cid]['score']:.3g} | {still} |")
    (args.out / "rerun.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
