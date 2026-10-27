"""Every tool miss of one or more practice runs, with its trajectory, grouped by family.

    .venv/bin/python tools/misses_by_trace.py RUN_DIR [RUN_DIR ...] > misses.md

For each question that scored below 1: the grader notes, the message as the agent received it, the lane,
the guidance and check events, which needed records reached the packet, each model call (reply excerpt,
tool calls, tool outputs) and the final text. Runs are matched to the local dataset by seed; traces are
matched to questions by request text.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from lab import data  # noqa: E402
from trace_compare import evidence_in_packet, match, purpose  # noqa: E402

EVENT_KEYS = ("guidance", "retry", "draft", "check", "route", "duplicate", "not sent", "blocked")


def main(runs: list[Path]) -> None:
    by_family: dict[str, list[str]] = collections.defaultdict(list)
    totals = []
    for run in runs:
        report = json.load(open(run / "report.json"))
        seed = int(report["seed"])
        per = [c for c in report["report"]["per_case"] if c.get("kind") == "tool"]
        totals.append((seed, run.name, sum(float(c["score"]) for c in per) / len(per), len(per)))
        cases = {c.key.rsplit("/", 1)[-1]: c for c in data.load(seed, 0, "full")}
        traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
        for row in per:
            if float(row["score"]) >= 0.999:
                continue
            case = cases[row["case_id"]]
            trace = match(case, traces)
            out = [f"### seed {seed} · {row['case_id']} · score {float(row['score']):.2f}",
                   f"- grader: {' | '.join(n for n in row.get('notes') or [] if 'observed via' not in n)[:400]}",
                   f"- expected: {case.answers or list(case.tools)}; called: {row.get('called')}"]
            if trace is None:
                by_family[case.kind] += out + ["- no trace matched", ""]
                continue
            out.append(f"- message: {trace['user_input'][:300]}")
            out.append(f"- lane: {trace['lane']}; records: {evidence_in_packet(case, trace)}")
            out.append(f"- events: {[e for e in trace.get('events') or [] if any(k in e for k in EVENT_KEYS)]}")
            for i, call in enumerate(trace["calls"], 1):
                calls = [(c["name"], json.dumps(c["args"], ensure_ascii=False)[:160]) for c in call.get("tool_calls") or []]
                reply = re.sub(r"\s+", " ", call.get("reply") or "")[:240]
                tool_out = [re.sub(r"\s+", " ", str(m.get("content")))[:200] for m in call["messages"] if m.get("role") == "tool"][-1:]
                line = f"  {i}. {purpose(call)}"
                if calls:
                    line += f" -> {calls}"
                out.append(line)
                if tool_out and i > 1:
                    out.append(f"     last tool output: {tool_out[0]}")
                if reply:
                    out.append(f"     reply: {reply}")
            out.append(f"- final: {re.sub(r'\\s+', ' ', trace.get('final_text') or '')[:400]}")
            by_family[case.kind] += out + [""]
    print("# Misses by trajectory\n")
    for seed, name, mean, n in totals:
        print(f"- seed {seed}: {mean:.3f} over {n} tool questions ({name})")
    print()
    for kind in sorted(by_family, key=lambda k: -sum(1 for line in by_family[k] if line.startswith("### "))):
        n = sum(1 for line in by_family[kind] if line.startswith("### "))
        print(f"## {kind} ({n})\n")
        print("\n".join(by_family[kind]))


if __name__ == "__main__":
    main([Path(p) for p in sys.argv[1:]])
