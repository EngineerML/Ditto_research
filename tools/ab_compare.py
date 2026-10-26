"""Compare repeated runs of two harness versions on the same questions, question by question.

    .venv/bin/python tools/ab_compare.py OUT.md --old RUN [RUN ...] --new RUN [RUN ...] [--cases FILE]

Every run is a report.json + trace.jsonl folder. Per question: how often each version passed
(score >= 0.999), and the mean score. A regression is a question that passed in every old run
and failed in at least one new run; a gain is the reverse. Both are listed with the new run's
answer, so each one can be read before the change is kept. Also: mean score, model calls and
seconds per version, and provider noise left in the new runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from flag_failed_calls import case_ids, latencies, reasons  # noqa: E402
from lab import data  # noqa: E402


def load(run: Path, cases: list) -> tuple[dict, dict]:
    rows = {c["case_id"]: c for c in json.load(open(run / "report.json"))["report"]["per_case"]}
    traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
    return rows, dict(zip(case_ids(traces, cases, latencies(list(rows.values()))), traces))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--old", nargs="+", type=Path, required=True)
    ap.add_argument("--new", nargs="+", type=Path, required=True)
    ap.add_argument("--cases", type=Path, help="only these case ids (default: those every run graded)")
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, args.size)
    by_id = {c.key.rsplit("/", 1)[-1]: c for c in cases}
    old = [load(run, cases) for run in args.old]
    new = [load(run, cases) for run in args.new]
    ids = set(args.cases.read_text().split()) if args.cases else set.intersection(*(set(r) for r, _ in old + new))
    ids = sorted(cid for cid in ids if all(cid in r for r, _ in old + new))

    def passes(side, cid):
        return [r[cid]["score"] >= 0.999 for r, _ in side]

    def mean(side, key):
        vals = [key(r, t, cid) for r, t in side for cid in ids]
        return sum(vals) / len(vals)

    lines = [f"# {len(ids)} questions, {len(old)} old run(s), {len(new)} new run(s)", "",
             "| | old | new |", "|---|---|---|"]
    lines.append(f"| mean score | {mean(old, lambda r, t, c: r[c]['score']):.3f} | {mean(new, lambda r, t, c: r[c]['score']):.3f} |")
    lines.append(f"| model calls / question | {mean(old, lambda r, t, c: len((t.get(c) or {}).get('calls', []))):.2f} | {mean(new, lambda r, t, c: len((t.get(c) or {}).get('calls', []))):.2f} |")
    lines.append(f"| seconds / question | {mean(old, lambda r, t, c: (t.get(c) or {}).get('seconds', 0)):.1f} | {mean(new, lambda r, t, c: (t.get(c) or {}).get('seconds', 0)):.1f} |")
    regress, gain, flip = [], [], []
    for cid in ids:
        o, n = passes(old, cid), passes(new, cid)
        line = f"| {cid} | {by_id[cid].kind} | {sum(o)}/{len(o)} | {sum(n)}/{len(n)} | {by_id[cid].answers} | " + \
               " / ".join(repr(((t.get(cid) or {}).get("answer") or "")[:60]) for _, t in new) + " |"
        if all(o) and not all(n):
            regress.append(line)
        elif not any(o) and any(n):
            gain.append(line)
        elif not ((all(o) and all(n)) or (not any(o) and not any(n))):
            flip.append(line)
    head = "| case | category | old passed | new passed | expected | new answers |\n|---|---|---|---|---|---|"
    lines += ["", f"## Regressions: passed every old run, failed a new one ({len(regress)})", "", head] + regress
    lines += ["", f"## Gains: failed every old run, passed a new one ({len(gain)})", "", head] + gain
    lines += ["", f"## Mixed both sides ({len(flip)})", "", head] + flip
    noise = [f"- {cid}: {'; '.join(sorted(set(reasons(t[cid]))))}" for _, t in new for cid in ids if cid in t and reasons(t[cid])]
    lines += ["", f"## Provider noise in the new runs ({len(noise)})", ""] + noise
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"regressions {len(regress)}, gains {len(gain)}, mixed {len(flip)}, noisy new trajectories {len(noise)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
