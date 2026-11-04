"""Bench the tool-list selector (toolselect.py) on the bench-16 served dumps (build_served.sh).

    python3 v16_atlas/select_bench.py [--half dev|test|all] [--misses N] [--json OUT]

Recall: share of tool cases whose every expected tool is offered (and the share of expected tools offered).
Size: tools and prompt tokens offered per request, for tool cases and memory cases (tokens = 0.13 x the tool's JSON
characters, measured on paired 36- and 235-tool calls of 2026-11-03).
Seeds alternate between halves by their line in corpus_seeds.txt: tune on dev, confirm on test.
"""
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import toolselect  # noqa: E402

TOKENS_PER_CHAR = 0.13

ap = argparse.ArgumentParser()
ap.add_argument("--half", default="dev", choices=["dev", "test", "all"])
ap.add_argument("--misses", type=int, default=25)
ap.add_argument("--json", default="")
args = ap.parse_args()

seeds = [s.strip() for s in (HERE / "corpus_seeds.txt").read_text().split()]
pick = {"dev": seeds[0::2], "test": seeds[1::2], "all": seeds}[args.half]
served = HERE.parent / ".cache" / "served16"

case_ok = case_n = exp_ok = exp_n = 0
by_cat = collections.defaultdict(lambda: [0, 0])
reasons = collections.Counter()
misses = []
tool_counts, tool_tokens, mem_counts, mem_tokens, full_tokens = [], [], [], [], []
for seed in pick:
    d = json.loads((served / f"v16_s{seed}.json").read_text())
    cat = d["catalog"]
    size = {t["name"]: len(json.dumps(t)) * TOKENS_PER_CHAR for t in cat}
    full_tokens.append(sum(size.values()))
    for c in d["tool_cases"]:
        names, why = toolselect.select(cat, c["prompt"])
        got = set(names)
        exp = [e for e in c.get("expected_tools") or [] if e in size]
        hit = all(e in got for e in exp)
        case_n += 1; case_ok += hit
        exp_n += len(exp); exp_ok += sum(e in got for e in exp)
        by_cat[c["category"]][0] += 1; by_cat[c["category"]][1] += hit
        tool_counts.append(len(names)); tool_tokens.append(sum(size[n] for n in names))
        reasons.update(why.values())
        if not hit:
            misses.append((c["category"], c["prompt"], [e for e in exp if e not in got]))
    for c in d["memory_cases"]:
        names, _ = toolselect.select(cat, c["question"])
        mem_counts.append(len(names)); mem_tokens.append(sum(size[n] for n in names))

print(f"half {args.half}: {len(pick)} seeds, {case_n} tool cases, {len(mem_counts)} memory cases")
print(f"recall: cases {case_ok}/{case_n} = {100*case_ok/case_n:.2f}%   expected tools {exp_ok}/{exp_n} = {100*exp_ok/exp_n:.2f}%")
print(f"catalog: {statistics.mean(len(json.loads((served / f'v16_s{s}.json').read_text())['catalog']) for s in pick[:5]):.0f} tools, {statistics.mean(full_tokens):,.0f} tokens")
print(f"tool cases:   offered {statistics.mean(tool_counts):5.1f} tools (p95 {sorted(tool_counts)[int(.95*len(tool_counts))]}, max {max(tool_counts)}), {statistics.mean(tool_tokens):6,.0f} tokens")
print(f"memory cases: offered {statistics.mean(mem_counts):5.1f} tools (p95 {sorted(mem_counts)[int(.95*len(mem_counts))]}, max {max(mem_counts)}), {statistics.mean(mem_tokens):6,.0f} tokens")
print("reasons per tool case:", {k: round(v / case_n, 1) for k, v in reasons.items()})
worst = sorted(((n - ok, k, ok, n) for k, (n, ok) in by_cat.items() if ok < n), reverse=True)
print("categories with misses:", [(k, f"{ok}/{n}") for _, k, ok, n in worst])
for cat_, prompt, lost in misses[: args.misses]:
    print(f"  MISS [{cat_}] {prompt[:140]!r} lost {lost}")
if args.json:
    Path(args.json).write_text(json.dumps({"half": args.half, "recall_cases": case_ok / case_n, "recall_tools": exp_ok / exp_n,
                                           "tool_tools": statistics.mean(tool_counts), "tool_tokens": statistics.mean(tool_tokens),
                                           "mem_tools": statistics.mean(mem_counts), "mem_tokens": statistics.mean(mem_tokens),
                                           "full_tokens": statistics.mean(full_tokens), "misses": misses}, indent=1))
