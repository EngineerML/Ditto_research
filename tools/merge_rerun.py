"""Merge a re-run of flagged questions back into its full practice run.

    .venv/bin/python tools/merge_rerun.py FULL_RUN RERUN_RUN OUT_DIR [--seed S] [--size full]

For each case id in RERUN_RUN/only_cases.txt, the full run's per-case score and trace row are
replaced by the re-run's, or added when the full run never got to that question (cases the
scorer only ran as a run-after dependency are not taken). A full run cut short has no
report.json; its graded results then come from the saved scorer_status.json. The merged
per-case scores are re-aggregated with the official scorer (.cache/ditto-rescore), so
composite, means and gate factors are the numbers the full run would have reported with
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
from flag_failed_calls import case_ids, graded_rows, latencies, reasons  # noqa: E402
from lab import data  # noqa: E402

RESCORE = HERE / ".cache" / "ditto-rescore"
GATE_KEYS = ("tool_efficiency", "metamorphic_consistency", "conversational_sanity", "memory_over_call")


def base_report(run: Path) -> dict:
    if (run / "report.json").is_file():
        return json.load(open(run / "report.json"))
    status = json.load(open(run / "scorer_status.json"))
    print(f"{run.name} was cut short: starting from its {len(status['partial'])} graded results", file=sys.stderr)
    return {"run_id": status["run_id"], "bench_version": status["bench_version"], "seed": status.get("seed"),
            "report": {"per_case": status["partial"], "details": {}, "composite": None, "tool_mean": None, "memory_mean": None}}


def traced(run: Path, cases: list) -> tuple[list[dict], list[str]]:
    traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
    return traces, case_ids(traces, cases, latencies(graded_rows(run)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("full", type=Path)
    ap.add_argument("rerun", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    wanted = (args.rerun / "only_cases.txt").read_text().split()

    full = base_report(args.full)
    redo = {c["case_id"]: c for c in graded_rows(args.rerun)}
    redo_traces, redo_ids = traced(args.rerun, cases)
    redo_trace = dict(zip(redo_ids, redo_traces))
    missing = [cid for cid in wanted if cid not in redo or cid not in redo_trace]
    if missing:
        print(f"re-run lacks {len(missing)} of the listed cases: {' '.join(missing)}", file=sys.stderr)
        return 1

    report = full["report"]
    before = {row["case_id"]: row for row in report["per_case"] if row["case_id"] in wanted}
    report["per_case"] = [row for row in report["per_case"] if row["case_id"] not in wanted]
    report["per_case"] += [dict(redo[cid], rerun_of_score=before[cid]["score"] if cid in before else None) for cid in wanted]

    full_traces, full_ids = traced(args.full, cases)
    merged = [t for t, cid in zip(full_traces, full_ids) if cid not in wanted]
    replaced = [t for t, cid in zip(full_traces, full_ids) if cid in wanted]
    merged += [dict(redo_trace[cid], rerun=True) for cid in wanted]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "trace.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in merged), encoding="utf-8")
    (args.out / "replaced.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in replaced), encoding="utf-8")

    (args.out / "report.json").write_text(json.dumps(full))
    rescored = json.loads(subprocess.run([str(RESCORE), str(args.out / "report.json")], capture_output=True, text=True, check=True).stdout)
    old = {k: report.get(k) for k in ("composite", "tool_mean", "memory_mean")} | {k: report["details"].get(k) for k in GATE_KEYS}
    for key in ("composite", "raw_composite", "tool_mean", "memory_mean", "conversational_sanity"):
        if key in rescored["report"]:
            report[key] = rescored["report"][key]
    report["details"].update(rescored["gates"])
    report["details"]["tool_mean"], report["details"]["memory_mean"] = report["tool_mean"], report["memory_mean"]
    report["merged_rerun"] = {"from": str(args.rerun), "cases": wanted, "before": old}
    (args.out / "report.json").write_text(json.dumps(full))

    lines = [f"# Re-run merged into {args.full.name}", "", f"re-run: {args.rerun.name}", "",
             f"{len(report['per_case'])} graded questions, {len(merged)} trajectories", "",
             "| | before | after |", "|---|---|---|"]
    lines += [f"| {k} | {old[k]} | {report[k] if k in report else report['details'].get(k)} |" for k in old]
    lines += ["", "| case | category | score before | after | re-run still hit |", "|---|---|---|---|---|"]
    for cid in wanted:
        was = f"{before[cid]['score']:.3g}" if cid in before else "not graded"
        still = "; ".join(sorted(set(reasons(redo_trace[cid])))) or "-"
        lines.append(f"| {cid} | {redo[cid]['category']} | {was} | {redo[cid]['score']:.3g} | {still} |")
    (args.out / "rerun.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
