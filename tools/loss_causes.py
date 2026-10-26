"""Sort every lost point of a traced run by where the trajectory went wrong.

    .venv/bin/python tools/loss_causes.py RUN_DIR [--seed S] [--size full] [--out FILE.md]

For each question scoring under 1:
- routing: the agent's lane is not the dataset's lane (records vs action);
- memory questions on the right lane: each evidence record the dataset names is looked up in
  what the model saw: in the first packet, or anywhere in any prompt (search passes, recall
  results, refills). "never seen" is a retrieval loss; "seen" means the evidence was in front
  of the model and the loop or prompt still produced the wrong answer;
- tool questions on the right lane: expected tools vs observed calls (restraint broken, the
  expected tool never called, a wrong tool, a result not used).
Prints a table per cause and category, and the questions under each.
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


def seen_text(trace: dict) -> str:
    parts = []
    for call in trace["calls"]:
        for message in call["messages"]:
            content = message.get("content")
            parts.append(content if isinstance(content, str) else json.dumps(content or "", ensure_ascii=False))
    return "\n".join(parts)


def key(text: str) -> str:
    # a stretch of the record that survives JSON escaping and snippets
    body = " ".join(text.split())
    return body[:50]


def memory_cause(case, trace: dict) -> tuple[str, str]:
    store = {r.pair_id: r for r in case.store}
    needs = [store[p] for p in sorted(case.needs) if p in store]
    if not needs:
        return "no evidence (absence / decline)", ""
    packet = " ".join(p[1] or "" for p in trace.get("packet") or [] if p and len(p) > 1)
    seen = seen_text(trace).replace("\\n", " ").replace('\\"', '"')
    seen = " ".join(seen.split())
    in_packet = sum(1 for r in needs if key(r.prompt)[:40] in " ".join(packet.split()))
    in_view = sum(1 for r in needs if key(r.prompt) in seen)
    detail = f"{in_view}/{len(needs)} evidence seen, {in_packet}/{len(needs)} in first packet"
    if in_view == 0:
        return "selection: evidence never seen", detail
    if in_view < len(needs):
        return "selection: part of the evidence seen", detail
    return "reasoning: all evidence seen, answer wrong", detail


def tool_cause(row: dict) -> tuple[str, str]:
    called, expected = row.get("called") or [], [t if isinstance(t, str) else t.get("name") for t in row.get("expected") or []]
    notes = " ".join(row.get("notes") or [])
    detail = f"called {called} expected {expected}"
    if "restraint" in notes and "acted instead" in notes:
        return "tool: acted where restraint was right", detail
    if not expected and called:
        return "tool: acted where restraint was right", detail
    if expected and not set(expected) & set(called):
        return ("tool: no call where one was needed" if not called else "tool: wrong tool"), detail
    return "tool: right tool, result or answer wrong", detail + " | " + notes[:120]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    by_id = {c.key.rsplit("/", 1)[-1]: c for c in cases}
    rows = {c["case_id"]: c for c in json.load(open(args.run / "report.json"))["report"]["per_case"]}
    traces = [json.loads(line) for line in open(args.run / "trace.jsonl", encoding="utf-8")]
    trace_of = dict(zip(case_ids(traces, cases, latencies(list(rows.values()))), traces))
    causes: dict[str, list[str]] = collections.defaultdict(list)
    points: collections.Counter = collections.Counter()
    for cid, row in rows.items():
        if row["score"] >= 0.999 or cid not in by_id or cid not in trace_of:
            continue
        case, trace = by_id[cid], trace_of[cid]
        lane = (trace.get("lane") or "?").split(":")[0]
        if row["category"].startswith("conversational-chitchat"):
            why, detail = "capped by policy (chitchat 0.5)", ""
        elif lane != case.lane:
            why, detail = f"routing: {lane} lane, dataset says {case.lane}", trace.get("lane")
        elif case.phase == "memory":
            why, detail = memory_cause(case, trace)
        else:
            why, detail = tool_cause(row)
        lost = 1 - row["score"]
        points[why] += lost
        causes[why].append(f"| {cid} | {case.phase}:{row['category']} | {row['score']:.2g} | {trace.get('lane')}/{trace.get('path')} | {detail[:150]} |")
    out = [f"# Lost points in {args.run.name}", "", "| cause | questions | points lost |", "|---|---|---|"]
    out += [f"| {why} | {len(causes[why])} | {points[why]:.1f} |" for why in sorted(causes, key=lambda w: -points[w])]
    out.append(f"| total | {sum(map(len, causes.values()))} | {sum(points.values()):.1f} |")
    for why in sorted(causes, key=lambda w: -points[w]):
        out += ["", f"## {why}", "", "| case | category | score | lane/path | detail |", "|---|---|---|---|---|"] + sorted(causes[why], key=lambda l: l.split("|")[2])
    text = "\n".join(out) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
