#!/usr/bin/env python3
"""How often DrPresident's product_tool (thint.py) names a coined tool for a request that does not mention it, and
whether skipping real words in its one-edit branch (the rule folded() already uses) loses any true match.

    .venv/bin/python practice/gates/product_tool_misfire.py [N_SEEDS]

Free: bench-15 datasets come from the local generator; no model call.
"""
import json
import os
import random
import re
import subprocess
import sys

sys.path.insert(0, "/home/bittensor/ditto/drp23v15")
from app.thint import COMMON, GENERIC_PARTS, WORD, one_edit, product_tool  # noqa: E402
from app.typofold import FOLD_WORDS, REAL_WORDS  # noqa: E402

GEN = "/home/bittensor/ditto/.cache/dittobench-generate-v15"
CACHE = "/home/bittensor/ditto/.cache/datasets"


def guarded(request: str, tool_names: list[str]) -> str:
    words = {re.sub(r"'s?$", "", word.lower()) for word in WORD.findall(request) if len(word) >= 4}
    slips = {word for word in words if word not in FOLD_WORDS and word not in REAL_WORDS and word not in COMMON}
    found = []
    for name in tool_names:
        part = name.lower().split("_")[0]
        if len(part) < 4 or part in GENERIC_PARTS:
            continue
        if part in words or (len(part) >= 5 and any(one_edit(part, word) for word in slips)):
            found.append(name)
    return found.pop() if len(found) == 1 else ""


def capitalised(request: str, tool_names: list[str]) -> str:
    """Only a capitalised word names a product: the brand as written, or one slip off it."""
    words = {re.sub(r"'s?$", "", word).lower() for word in WORD.findall(request) if len(word) >= 4 and word[0].isupper()}
    found = []
    for name in tool_names:
        part = name.lower().split("_")[0]
        if len(part) < 4 or part in GENERIC_PARTS:
            continue
        if part in words or (len(part) >= 5 and any(one_edit(part, word) for word in words)):
            found.append(name)
    return found.pop() if len(found) == 1 else ""


RULE = guarded if os.environ.get("RULE", "guard") == "guard" else capitalised


def dataset(seed: int) -> dict:
    path = f"{CACHE}/v15_s{seed}_salt0_full.json"
    if not os.path.exists(path):
        subprocess.run([GEN, "-bench-version", "15", "-seed", str(seed), "-run-size", "full", "-out", path], check=True, capture_output=True)
    return json.load(open(path))


n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rng = random.Random(118)
seeds = [5119792693744740612, 2190058953981709433, 6007065558233246269, 2497187654609273566] + [rng.getrandbits(63) for _ in range(n - 4)]
totals = dict(requests=0, fired=0, fired_guarded=0, false_before=0, false_after=0, true_before=0, true_lost=0)
examples = []
for seed in seeds:
    d = dataset(seed)
    names = [t["name"] for t in d["catalog"] if not t.get("description", "").rstrip().endswith("connector to be linked in Settings.")]
    requests = [(c["prompt"], [e["name"] for e in c.get("expected_tools") or []], c["category"]) for c in d["tool_cases"]]
    requests += [(c["question"], [], c["question_type"]) for c in d["memory_cases"]]
    for text, expected, category in requests:
        totals["requests"] += 1
        before, after = product_tool(text, names), RULE(text, names)
        if before:
            totals["fired"] += 1
            if before in expected:
                totals["true_before"] += 1
                if after != before:
                    totals["true_lost"] += 1
                    examples.append(("LOST", seed, category, before, text))
            else:
                totals["false_before"] += 1
                if len(examples) < 40:
                    examples.append(("FALSE", seed, category, before, text))
        if after:
            totals["fired_guarded"] += 1
            if after not in expected:
                totals["false_after"] += 1
                examples.append(("STILL FALSE", seed, category, after, text))
print(f"seeds {len(seeds)}: {totals}")
print(f"false fires per seed: before {totals['false_before'] / len(seeds):.2f}, after {totals['false_after'] / len(seeds):.2f}; true matches lost {totals['true_lost']}")
for kind, seed, category, tool, text in examples[:40]:
    print(f"  {kind:<11} seed {str(seed)[:6]} {category:<36} -> {tool:<28} {text[:110]!r}")
