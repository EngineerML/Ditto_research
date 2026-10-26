"""Two traced practice runs of one dataset, side by side: scores, gates, twins, and every trajectory worth reading.

    .venv/bin/python tools/compare_agents.py OUT_DIR A=RUN_DIR B=RUN_DIR [--seed S] [--size full]

Writes to OUT_DIR:
- summary.md: composite, tool and memory means and every gate for both runs, then per category
  where the runs differ;
- twins.md: every memory twin group (the consistency gate), all members, both runs, pass or fail;
- gates.md: the cases behind the gates: tool cases with more calls than expected, memory cases
  with a non-memory call, decision twins, conversation, canary and injection cases;
- cases.md: one block per kept case (all twins, all gate cases, every case either run scored
  below 1 or the runs scored differently): routing, records shown, every model call, answer;
- full/<kind>_<case>.md: every prompt and reply of those cases.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))
from lab import data  # noqa: E402
from trace_compare import dump  # noqa: E402
from trace_multi import block, match  # noqa: E402

GATES = ("metamorphic_consistency", "tool_efficiency", "memory_over_call", "conversational_sanity")
G_CATEGORIES = ("conversational", "canary", "injection", "declarative")


def called(row: dict) -> list[str]:
    return [c.get("name") if isinstance(c, dict) else str(c) for c in row.get("called") or []]


def gate_reasons(case: data.Case, row: dict | None) -> list[str]:
    if row is None:
        return []
    reasons = []
    names = called(row)
    if case.phase == "tool" and case.tools and len(names) > len(case.tools):
        reasons.append(f"extra calls ({len(names)} vs {len(case.tools)} expected)")
    if case.phase == "memory" and any(n not in data.MEMORY_READS for n in names):
        reasons.append("memory over-call: " + ", ".join(n for n in names if n not in data.MEMORY_READS))
    if row.get("relation") == "decision_twin":
        reasons.append("decision twin")
    if any(word in (row.get("category") or "") for word in G_CATEGORIES):
        reasons.append(row.get("category"))
    return reasons


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("runs", nargs=2)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    runs = []
    for spec in args.runs:
        label, path = spec.split("=", 1)
        run = Path(path)
        report = json.load(open(run / "report.json"))["report"]
        traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")] if (run / "trace.jsonl").is_file() else []
        runs.append((label, run, report, {c["case_id"]: c for c in report["per_case"]}, traces))
    (args.out / "full").mkdir(parents=True, exist_ok=True)
    (args.out / "cases.md").write_text("", encoding="utf-8")

    summary = ["# Runs", ""]
    summary.append("| | " + " | ".join(label for label, *_ in runs) + " |")
    summary.append("|---|" + "---|" * len(runs))
    for key in ("composite", "tool_mean", "memory_mean"):
        summary.append(f"| {key} | " + " | ".join(f"{r[key]:.4f}" for _, _, r, _, _ in runs) + " |")
    for key in GATES:
        summary.append(f"| {key} | " + " | ".join(str(r["details"].get(key)) for _, _, r, _, _ in runs) + " |")
    summary.append(f"| model calls | " + " | ".join(str(sum(len(t["calls"]) for t in tr)) for *_, tr in runs) + " |")
    summary.append(f"| prompt tokens (M) | " + " | ".join(f"{sum(c['prompt_tokens'] for t in tr for c in t['calls']) / 1e6:.2f}" for *_, tr in runs) + " |")

    keep: dict[str, list[str]] = {}
    twins: dict[str, list[tuple[data.Case, list]]] = collections.defaultdict(list)
    gate_lines: list[str] = []
    by_kind: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
    for case in cases:
        cid = case.key.rsplit("/", 1)[-1]
        rows = [rows_by.get(cid) for _, _, _, rows_by, _ in runs]
        traces = [match(case, row, tr) if row is not None else None for row, (_, _, _, _, tr) in zip(rows, runs)]
        scores = [None if r is None else r.get("score") for r in rows]
        if all(s is not None for s in scores):
            by_kind[f"{case.phase}:{case.kind}"].append(tuple(scores))
        reasons = []
        relation = next((r.get("relation") for r in rows if r and r.get("relation")), None)
        group = next((r.get("twin_group") for r in rows if r and r.get("twin_group")), None)
        if group and relation != "decision_twin" and case.phase == "memory":
            twins[group].append((case, rows))
            reasons.append(f"twin {relation}")
        for (label, *_), row in zip(runs, rows):
            g = gate_reasons(case, row)
            if g:
                reasons.append(f"{label}: " + "; ".join(g))
                gate_lines.append(f"- {label} {case.phase}:{case.kind} ({cid}) score {row.get('score')} called {called(row)} — {'; '.join(g)} | {case.text[:140]}")
        if any(s is not None and s < 0.999 for s in scores):
            reasons.append("below 1")
        if len({s for s in scores if s is not None}) > 1:
            reasons.append("runs differ")
        if reasons:
            keep[cid] = reasons
            lines = ["", "=" * 110, f"{case.phase}:{case.kind}  ({cid})  dataset lane {case.lane}  relation {relation}  twin {group}",
                     f"  why kept: {' / '.join(reasons)}", f"  Q: {case.text[:600]}", f"  answer key: {case.answers or list(case.tools)}"]
            for (label, *_), row, trace in zip(runs, rows, traces):
                lines += block(label, case, row, trace)
                if trace is not None:
                    lines.append(f"      path {trace.get('path')}  packet {len(trace.get('packet') or [])} records, {trace.get('packet_chars')} chars")
            (args.out / "cases.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
            dump(args.out / "full" / f"{case.kind}_{cid}.md", case, [(f"{label} {run.name}", row, tr) for (label, run, *_), row, tr in zip(runs, rows, traces)])

    summary += ["", "# Categories where the runs differ (mean score)", "", "| category | n | " + " | ".join(l for l, *_ in runs) + " |", "|---|---|" + "---|" * len(runs)]
    for kind, pairs in sorted(by_kind.items()):
        means = [statistics.mean(p[i] for p in pairs) for i in range(len(runs))]
        if max(means) - min(means) > 1e-9:
            summary.append(f"| {kind} | {len(pairs)} | " + " | ".join(f"{m:.3f}" for m in means) + " |")
    (args.out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    tw = ["# Memory twin groups (consistency gate)", ""]
    def correct(row: dict | None) -> bool:
        return row is not None and (row.get("score") or 0) >= 0.999

    for label_index, (label, *_) in enumerate(runs):
        split = sum(1 for members in twins.values() if len({correct(r[label_index]) for _, r in members}) > 1)
        tw.append(f"- {label}: {len(twins)} groups, {split} split")
    for group, members in sorted(twins.items()):
        marks = ["SPLIT" if len({correct(r[i]) for _, r in members}) > 1 else "ok" for i in range(len(runs))]
        tw += ["", f"## {group}  (" + ", ".join(f"{label} {mark}" for (label, *_), mark in zip(runs, marks)) + ")"]
        for case, rows in members:
            tw.append(f"- {rows[0].get('relation') if rows[0] else '?'} / {case.kind} ({case.key.rsplit('/', 1)[-1]}): " +
                      "  ".join(f"{label}={'-' if r is None else r.get('score')}" for (label, *_), r in zip(runs, rows)) +
                      f" | key {case.answers} | {case.text[:120]}")
    (args.out / "twins.md").write_text("\n".join(tw) + "\n", encoding="utf-8")
    (args.out / "gates.md").write_text("# Cases behind the gates\n\n" + "\n".join(gate_lines) + "\n", encoding="utf-8")
    print(f"kept {len(keep)} cases, {len(twins)} memory twin groups -> {args.out}")


if __name__ == "__main__":
    main()
