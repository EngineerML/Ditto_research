"""Memory-only runs (250 questions) of the given labels: memory mean, gate metrics, program splits, losses.

    python3 practice/gates/memory_summary.py LABEL [LABEL ...]

Per run: memory mean; the quality metrics the report's details carry (consistency, conversational sanity,
memory over-call); claim-provenance flags; program score and twin splits (shape oracle); points lost per category.
Categories capped by construction (parser-divergence at 1/3, chitchat at 0.5) are shown with their cap."""
import glob
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
from v14_oracle import shapes  # noqa: E402

CAPS = {"conversational-chitchat": 0.5, "parser-divergence-negation": 1 / 3, "parser-divergence-retraction": 1 / 3,
        "parser-divergence-reported-speech": 1 / 3}


def find(node, key):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                return v
            found = find(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = find(v, key)
            if found is not None:
                return found
    return None


labels = sys.argv[1:]
lost_all = defaultdict(lambda: defaultdict(float))
for run in sorted(glob.glob("/home/bittensor/ditto/practice/2026*_ditto-harness-*_full*")):
    label = re.search(r"ditto-harness-(.+?)_full", run).group(1)
    if label not in labels:
        continue
    try:
        rep = json.load(open(f"{run}/report.json"))
    except (OSError, ValueError):
        continue
    body = rep.get("report") or {}
    cases = body.get("per_case") or []
    if rep.get("bench_version") != 14 or len(cases) < 200:
        continue
    seed = int(rep["seed"])
    oracle = shapes(seed)
    details = body.get("details") or {}
    groups = defaultdict(list)
    program = 0.0
    lost = defaultdict(float)
    for c in cases:
        cid = c["case_id"].rsplit("/", 1)[-1]
        cap = CAPS.get(c["category"], 1.0)
        lost[c["category"]] += max(0.0, cap - c["score"])
        if cid in oracle:
            program += c["score"]
            if oracle[cid].relation != "counterfactual":
                groups[(oracle[cid].domain, oracle[cid].group)].append(c["score"] >= 0.5)
    splits = sum(1 for g in groups.values() if any(g) and not all(g))
    for k, v in lost.items():
        lost_all[label][k] += v
    metrics = {k: find(details, k) for k in ("metamorphic_consistency", "conversational_sanity", "memory_over_call")}
    aip = find(details, "answer_in_prompt_cases")
    print(f"{label:9} seed {seed:>20} memory {body.get('memory_mean'):.3f}  program {program:4.1f}/40 splits {splits}  "
          f"gates {json.dumps(metrics)[:160]}  answer_in_prompt {aip}  lost(uncapped beyond caps) {sum(lost.values()):.1f}")
for label in labels:
    top = sorted(lost_all[label].items(), key=lambda kv: -kv[1])[:12]
    print(f"\n{label}: points lost beyond the caps, by category (all its runs): " + ", ".join(f"{k} {v:.1f}" for k, v in top))
