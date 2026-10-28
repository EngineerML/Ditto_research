"""Every traced practice run of every seed, side by side for each tool question any of them missed.

    .venv/bin/python tools/trace_many.py OUT_DIR [--since 20261026]

Finds every practice run with a trace and a report (merged composites left out), groups them by
seed, and for each tool question that scored below 1 in at least one run writes:

- OUT_DIR/full/<seed>_<family>_<case>.md: every run's whole trajectory (all messages, replies,
  tool calls and tool outputs of every model call), via trace_compare.dump;
- OUT_DIR/families/<family>.md: per question and run, the score, grader notes, lane, whether the
  needed records reached the packet, each model call (purpose, reply excerpt, tool calls, the
  tool output it got) and the final text;
- OUT_DIR/table.md: per family and version, solved / runs.

Runs are labelled by their harness tag (combined-horizon, combined-v4b, dan0l-v24-trace, ...).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from lab import data  # noqa: E402
from trace_compare import dump, effort, evidence_in_packet, match, purpose  # noqa: E402


def runs_by_seed(since: str, phase: str = "tool") -> dict[tuple[int, int], list[tuple[str, Path]]]:
    """Traced runs that graded questions of this phase, by (seed, bench version)."""
    found = collections.defaultdict(list)
    for d in sorted(glob.glob(str(HERE / "practice" / "2026*"))):
        path = Path(d)
        if path.name < since or "merged" in path.name:
            continue
        if not ((path / "trace.jsonl").is_file() and (path / "report.json").is_file()):
            continue
        try:
            report = json.load(open(path / "report.json"))
        except ValueError:
            continue
        per = report.get("report", {}).get("per_case") or []
        if not any((c.get("kind") == "tool") == (phase == "tool") for c in per) or report.get("seed") is None:
            continue
        label = re.search(r"ditto-harness-([\w-]+?)_(?:full|small|medium)", path.name).group(1)
        bench = int(report.get("bench_version") or 13)
        found[(int(report["seed"]), bench)].append((f"{label}{'' if bench == 13 else f'@v{bench}'} {path.name[:16]}", path))
    return found


def tool_outputs(call: dict) -> list[str]:
    return [re.sub(r"\s+", " ", str(m.get("content")))[:300] for m in call["messages"] if m.get("role") == "tool"]


def summary(case: data.Case, name: str, row: dict | None, trace: dict | None) -> list[str]:
    if row is None:
        return [f"### {name}: not in this run"]
    out = [f"### {name}: score {row.get('score')}, called {row.get('called')}, lane {trace.get('lane') if trace else '?'}"]
    out.append(f"- grader: {' | '.join(n for n in row.get('notes') or [] if 'trajectory observed' not in n)[:500]}")
    if trace is None:
        out.append("- no trace matched")
        return out
    out.append(f"- records: {evidence_in_packet(case, trace)}; events: {', '.join((trace.get('events') or []))[:600]}")
    seen_outputs: set[str] = set()
    for i, call in enumerate(trace["calls"], 1):
        s = call["settings"]
        calls = f" -> {json.dumps([(c['name'], c['args']) for c in call['tool_calls']], ensure_ascii=False)[:400]}" if call["tool_calls"] else ""
        out.append(f"  {i:2d}. {purpose(call)} (effort {effort(s)}, temp {s.get('temperature')}){calls}")
        for text in tool_outputs(call):
            if text not in seen_outputs:
                seen_outputs.add(text)
                out.append(f"      tool output: {text}")
        reply = re.sub(r"\s+", " ", call["reply"] or "")[:300]
        if reply:
            out.append(f"      reply: {reply}")
    out.append(f"- final: {re.sub(r'\\s+', ' ', trace.get('final_text') or '')[:500]}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--since", default="20261026")
    ap.add_argument("--phase", choices=("tool", "memory"), default="tool")
    args = ap.parse_args()
    (args.out / "full").mkdir(parents=True, exist_ok=True)
    (args.out / "families").mkdir(parents=True, exist_ok=True)
    families: dict[str, list[str]] = collections.defaultdict(list)
    table: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for (seed, bench), runs in sorted(runs_by_seed(args.since, args.phase).items()):
        data.BENCH = bench
        cases = [c for c in data.load(seed, 0, "full") if (c.phase == "tool") == (args.phase == "tool")]
        loaded = []
        for name, path in runs:
            report = json.load(open(path / "report.json"))["report"]
            rows = {c["case_id"]: c for c in report["per_case"]}
            traces = [json.loads(line) for line in open(path / "trace.jsonl", encoding="utf-8")]
            loaded.append((name, rows, traces))
        for case in cases:
            cid = case.key.rsplit("/", 1)[-1]
            rows = [(name, rows.get(cid), traces) for name, rows, traces in loaded]
            for name, row, _ in rows:
                if row is not None:
                    cell = table[case.kind][name.split()[0]]
                    cell[1] += 1
                    cell[0] += float(row.get("score") or 0) >= 0.999
            if not any(row is not None and float(row.get("score") or 0) < 0.999 for _, row, _ in rows):
                continue
            matched = [(name, row, match(case, traces) if row is not None else None) for name, row, traces in rows]
            dump(args.out / "full" / f"{seed}_{case.kind}_{cid}.md", case, [(n, r, t) for n, r, t in matched if r is not None])
            lines = ["", f"## seed {seed} · {cid}", "", f"Question: {case.text}", "", f"Answer key: {case.answers or list(case.tools)}; truth lane {case.lane}", ""]
            for name, row, trace in matched:
                if row is not None:
                    lines += summary(case, name, row, trace) + [""]
            families[case.kind] += lines
    for kind, lines in families.items():
        (args.out / "families" / f"{kind}.md").write_text(f"# {kind}\n" + "\n".join(lines), encoding="utf-8")
    versions = sorted({v for cells in table.values() for v in cells})
    out = ["| family | " + " | ".join(versions) + " |", "|---|" + "---|" * len(versions)]
    for kind in sorted(table):
        if kind not in families:
            continue
        out.append(f"| {kind} | " + " | ".join(f"{table[kind][v][0]}/{table[kind][v][1]}" if table[kind][v][1] else "" for v in versions) + " |")
    (args.out / "table.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(families)} families with a miss; files in {args.out}")


if __name__ == "__main__":
    main()
