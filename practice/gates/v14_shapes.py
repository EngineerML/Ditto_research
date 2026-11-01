"""Program questions by exact v14 generator shape, over every local bench-14 run with a report.

The shape of each case comes from v14_oracle (recomputed from the seed): chain template and cue mode,
process, sequence, as-of, membership, custody, identity join, and the carried families. Per shape and
harness label: cases right / total, and twin groups split ("s").

    .venv/bin/python practice/gates/v14_shapes.py [label-prefix ...] [--misses SHAPE-PREFIX] [--census]
"""
import difflib
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

from v14_oracle import shapes

ROOT = "/home/bittensor/ditto"
PROGRAM = ("v13-open-program", "v13-personal-program")
SCOPE_RE = re.compile(r"\bc[0-9a-f]{16}\b")


def label(run: str) -> str:
    m = re.search(r"ditto-harness-(.+?)_full", run)
    return m.group(1) if m else run


def runs(prefixes: list[str]):
    for d in sorted(glob.glob(f"{ROOT}/practice/2026[01][01]*")):
        try:
            rep = json.load(open(f"{d}/report.json"))
        except (OSError, ValueError):
            continue
        if rep.get("bench_version") != 14:
            continue
        name = label(d)
        if prefixes and not any(name.startswith(p) for p in prefixes):
            continue
        body = rep.get("report") if isinstance(rep.get("report"), dict) else {}
        yield d, name, rep.get("seed"), body.get("per_case") or rep.get("partial") or []


def traces(run: str) -> dict[str, list[dict]]:
    """Scope token of the question -> traces; the served question is clean, the dataset's is typo'd."""
    out: dict[str, list[dict]] = defaultdict(list)
    try:
        for line in open(f"{run}/trace.jsonl"):
            t = json.loads(line)
            m = SCOPE_RE.search(t.get("user_input") or "")
            if m:
                out[m.group(0)].append(t)
    except OSError:
        pass
    return out


def trace_for(question: str, by_scope: dict[str, list[dict]]) -> dict:
    m = SCOPE_RE.search(question)
    found = by_scope.get(m.group(0), []) if m else []
    if not found:
        return {}
    return max(found, key=lambda t: difflib.SequenceMatcher(None, t["user_input"], question).ratio())


def census() -> None:
    counts: Counter[str] = Counter()
    seeds = glob.glob(f"{ROOT}/.cache/datasets/v14_s*_salt0_full.json")
    for path in seeds:
        seed = int(re.search(r"_s(\d+)_", path).group(1))
        for s in shapes(seed).values():
            if s.relation == "base":
                counts[s.label] += 1
    print(f"twin groups per seed, by shape, over {len(seeds)} seeds:")
    for kind, n in counts.most_common():
        print(f"  {n / len(seeds):5.2f}  {kind}")


def main() -> None:
    argv = sys.argv[1:]
    misses = None
    if "--misses" in argv:
        at = argv.index("--misses")
        misses = argv[at + 1]
        del argv[at:at + 2]
    if "--census" in argv:
        census()
        return
    prefixes = [a for a in argv if not a.startswith("--")]
    tally: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    split: dict[str, Counter[str]] = defaultdict(Counter)
    run_count: Counter[str] = Counter()
    datasets: dict[int, dict[str, dict]] = {}
    for d, name, seed, cases in runs(prefixes):
        if seed not in datasets:
            path = f"{ROOT}/.cache/datasets/v14_s{seed}_salt0_full.json"
            data = json.load(open(path)) if os.path.exists(path) else {"memory_cases": []}
            datasets[seed] = {c["id"]: c for c in data["memory_cases"] if c["question_type"] in PROGRAM}
        known = datasets[seed]
        if not known:
            continue
        oracle = shapes(seed)
        run_count[name] += 1
        by_scope = traces(d) if misses else {}
        groups: dict[tuple[str, str], list[float]] = defaultdict(list)
        for c in cases:
            case = known.get(c.get("case_id"))
            shape = oracle.get(c.get("case_id"))
            if case is None or shape is None:
                continue
            score = c.get("score") or 0
            cell = tally[shape.label][name]
            cell[0] += score >= 1
            cell[1] += 1
            if shape.relation != "counterfactual":
                groups[(f"{shape.domain}-{shape.group}", shape.label)].append(score)
            if misses is not None and shape.label.startswith(misses) and score < 1:
                t = trace_for(case["question"], by_scope)
                answer = (t.get("answer") or t.get("final_text") or "")[-240:].replace("\n", " ⏎ ")
                print(f"--- {name} {os.path.basename(d)[:16]} [{shape.label} {shape.domain} {shape.relation}] expected {case['expected_answer']!r}")
                print(f"    Q: {t.get('user_input', case['question'])[:200]}")
                print(f"    A: {answer!r}")
                print(f"    path {t.get('path')} events {[e for e in (t.get('events') or []) if 'draft' in e or 'check' in e][:4]}")
        for (_, kind), scores in groups.items():
            if len(scores) > 1 and any(s >= 1 for s in scores) and any(s < 1 for s in scores):
                split[kind][name] += 1
    if misses is not None:
        return
    names = sorted(run_count)
    print("runs: " + ", ".join(f"{n}×{run_count[n]}" for n in names))
    width = max(len(k) for k in tally) if tally else 10
    print(f"{'shape':{width}}  " + "  ".join(f"{n[:14]:>14}" for n in names))
    for kind in sorted(tally):
        cells = []
        for n in names:
            right, total = tally[kind].get(n, [0, 0])
            s = split[kind].get(n, 0)
            cells.append(f"{right}/{total}{' s' + str(s) if s else ''}" if total else "")
        print(f"{kind:{width}}  " + "  ".join(f"{c:>14}" for c in cells))


if __name__ == "__main__":
    main()
