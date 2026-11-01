"""Per seed: a graded replay (replay_v8.py output) against the graded runs of other labels on the same seeds.

    python3 practice/gates/compare_replay.py REPLAY.json LABEL [LABEL ...]

Score out of 40, twin groups split (s), groups wrong on all three rewordings (w); then per shape, right / total."""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
sys.path.insert(0, "/home/bittensor/ditto/practice/gates/grader_probe")
from program_replies import replies  # noqa: E402
from v14_oracle import shapes  # noqa: E402

replay = json.load(open(sys.argv[1]))
labels = sys.argv[2:]
seeds = sorted({m["seed"] for m in replay})


def summary(cases: list[tuple[str, float]], seed: int) -> tuple[float, int, int]:
    oracle = shapes(seed)
    groups = defaultdict(list)
    for cid, score in cases:
        if oracle[cid].relation != "counterfactual":
            groups[(oracle[cid].domain, oracle[cid].group)].append(score >= 0.5)
    split = sum(1 for g in groups.values() if any(g) and not all(g))
    wrong = sum(1 for g in groups.values() if not any(g))
    return round(sum(score for _, score in cases), 1), split, wrong


runs = defaultdict(lambda: defaultdict(list))
for r in replies(labels):
    runs[(r["label"], r["seed"])][r["run"]].append((r["id"], r["score"]))
by_shape = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for r in replies(labels):
    if r["seed"] in seeds:
        cell = by_shape[shapes(r["seed"])[r["id"]].label][r["label"]]
        cell[0] += r["score"] >= 0.5
        cell[1] += 1
for m in replay:
    cell = by_shape[shapes(m["seed"])[m["id"]].label]["replay"]
    cell[0] += m["new_score"] >= 0.5
    cell[1] += 1

print(f"{'seed':>20} " + " ".join(f"{label:>24}" for label in [*labels, "replay"]))
totals = defaultdict(lambda: [0, 0.0, 0, 0])
for seed in seeds:
    cells = []
    for label in labels:
        found = [summary(cases, seed) for cases in runs[(label, seed)].values()]
        for s, sp, w in found:
            t = totals[label]
            t[0] += 1; t[1] += s; t[2] += sp; t[3] += w
        cells.append(" ".join(f"{s:g}/s{sp}w{w}" for s, sp, w in found) or "-")
    s, sp, w = summary([(m["id"], m["new_score"]) for m in replay if m["seed"] == seed], seed)
    t = totals["replay"]
    t[0] += 1; t[1] += s; t[2] += sp; t[3] += w
    cells.append(f"{s:g}/s{sp}w{w}")
    print(f"{seed:>20} " + " ".join(f"{cell:>24}" for cell in cells))
print("per run:")
for label in [*labels, "replay"]:
    n, s, sp, w = totals[label]
    if n:
        print(f"  {label:14} runs {n:2}  score {s / n:5.2f}  splits {sp / n:4.2f}  all-wrong {w / n:4.2f}")
print(f"\n{'shape':40} " + " ".join(f"{label:>12}" for label in [*labels, "replay"]))
for shape in sorted(by_shape):
    print(f"{shape:40} " + " ".join(f"{'%d/%d' % tuple(by_shape[shape][label]) if by_shape[shape][label][1] else '':>12}" for label in [*labels, "replay"]))
