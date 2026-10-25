"""Every traced practice run of one dataset, lined up per question.

    .venv/bin/python tools/trace_multi.py OUT_DIR LABEL=RUN [LABEL=RUN ...] [--seed 4242] [--size full]

Labels starting with "H" count as Hades runs, the rest as ours. A question is kept when any
valid observation scored below 1 or two observations of one system disagree. Observations
whose trace shows a payment or credit error are marked invalid and left out of the scores.

Writes OUT_DIR/cases.md (one compact block per kept question: answer key, and per run the
score, grader notes, called tools, routed lane against the dataset's lane, needed records in
the packet, every model call with purpose, size and reply excerpt, and the final answer),
OUT_DIR/full/<kind>_<case>.md with every prompt and reply, OUT_DIR/groups.md (twin groups
and the split ones per run) and OUT_DIR/summary.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))
from lab import data  # noqa: E402
from trace_compare import dump, effort, evidence_in_packet, match, purpose  # noqa: E402

PAYMENT = re.compile(r"\b402\b|Payment Required|insufficient credits", re.IGNORECASE)


def invalid(trace: dict | None) -> bool:
    return bool(trace) and any(PAYMENT.search(str(e)) for e in trace.get("events") or [])


def lane_of(trace: dict | None) -> str:
    return ((trace or {}).get("lane") or "-").split(":")[0]


def block(label: str, case: data.Case, row: dict | None, trace: dict | None) -> list[str]:
    if row is None:
        return [f"  [{label}] not in this run"]
    flag = "  INVALID (credit error)" if invalid(trace) else ""
    out = [f"  [{label}] score {row.get('score')}  called {[c.get('name') if isinstance(c, dict) else c for c in row.get('called') or []]}"
           f"  lane {(trace or {}).get('lane')} (dataset lane {case.lane}){flag}",
           f"      notes: {' | '.join(row.get('notes') or [])[:500]}"]
    if trace is None:
        return out + ["      no trace"]
    out.append(f"      records: {evidence_in_packet(case, trace)}   model calls {len(trace['calls'])}   {trace.get('seconds')}s")
    for i, call in enumerate(trace["calls"], 1):
        s = call["settings"]
        calls = f" -> {[(c['name'], c['args']) for c in call['tool_calls']]}"[:400] if call["tool_calls"] else ""
        reply = re.sub(r"\s+", " ", call["reply"] or "")[:260]
        out.append(f"      {i:2d}. {purpose(call):26s} effort={effort(s)} in={call['prompt_tokens']} out={call['completion_tokens']} "
                   f"finish={call['finish']}{calls}")
        if reply:
            out.append(f"          reply: {reply}")
    events = [str(e)[:160] for e in trace.get("events") or []]
    if events:
        out.append(f"      events: {events[:8]}")
    out.append(f"      final answer: {trace.get('answer')!r}")
    out.append(f"      final text: {re.sub(r'\s+', ' ', trace.get('final_text') or '')[:400]}")
    return out


def correct(row: dict) -> bool:
    return (row.get("score") or 0) >= 0.999


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--size", default="full")
    ap.add_argument("--salt", type=int, default=0)
    args = ap.parse_args()
    cases = data.load(args.seed, args.salt, args.size)
    runs = []
    for spec in args.runs:
        label, path = spec.split("=", 1)
        run = Path(path)
        report = json.load(open(run / "report.json"))["report"]
        traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
        runs.append((label, run, {c["case_id"]: c for c in report["per_case"]}, traces))
    (args.out / "full").mkdir(parents=True, exist_ok=True)
    blocks, summary, groups = [], [], {}
    for case in cases:
        cid = case.key.rsplit("/", 1)[-1]
        obs = []
        for label, run, rows, traces in runs:
            row = rows.get(cid)
            trace = match(case, traces) if row is not None else None
            obs.append((label, row, trace))
        valid = [(lab, row) for lab, row, tr in obs if row is not None and not invalid(tr)]
        for lab, row in valid:
            if row.get("twin_group"):
                groups.setdefault((lab, row["twin_group"]), []).append((row.get("relation"), case.kind, correct(row), cid))
        flips = {sys_: {correct(r) for lab, r in valid if lab.startswith("H") == (sys_ == "H")} for sys_ in ("H", "O")}
        low = any(not correct(r) for _, r in valid)
        flip = any(len(v) > 1 for v in flips.values())
        if not (low or flip):
            continue
        summary.append({"case": cid, "phase": case.phase, "kind": case.kind, "lane": case.lane, "question": case.text,
                        "scores": {lab: (None if row is None else (None if invalid(tr) else row.get("score"))) for lab, row, tr in obs},
                        "routed": {lab: lane_of(tr) for lab, row, tr in obs if tr is not None},
                        "twin_group": next((r.get("twin_group") for _, r, _ in obs if r and r.get("twin_group")), None),
                        "relation": next((r.get("relation") for _, r, _ in obs if r and r.get("relation")), None),
                        "category": next((r.get("category") for _, r, _ in obs if r), None)})
        lines = ["", "=" * 110, f"{case.phase}:{case.kind}  ({cid})  dataset lane {case.lane}  "
                 f"category {summary[-1]['category']}  relation {summary[-1]['relation']}  twin {summary[-1]['twin_group']}",
                 f"  Q: {case.text[:600]}", f"  answer key: {case.answers or list(case.tools)}"]
        for label, row, trace in obs:
            lines += block(label, case, row, trace)
        blocks.append("\n".join(lines))
        dump(args.out / "full" / f"{case.kind}_{cid}.md", case, [(f"{lab} {run.name}", row, tr) for (lab, row, tr), (_, run, _, _) in zip(obs, runs)])
    (args.out / "cases.md").write_text("\n".join(blocks), encoding="utf-8")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    glines = []
    for label, *_ in runs:
        mine = {g: v for (lab, g), v in groups.items() if lab == label}
        split = {g: v for g, v in mine.items() if len({ok for rel, _, ok, _ in v if rel != "decision_twin"}) > 1}
        glines.append(f"## {label}: {len(mine)} twin groups, {len(split)} split (non-decision members)")
        for g, v in sorted(mine.items()):
            mark = "SPLIT" if g in split else ""
            glines.append(f"  {g} {mark} " + ", ".join(f"{rel}/{kind}={'1' if ok else '0'}({cid[:7]})" for rel, kind, ok, cid in v))
    (args.out / "groups.md").write_text("\n".join(glines), encoding="utf-8")
    print(f"kept {len(summary)} questions -> {args.out}")


if __name__ == "__main__":
    main()
