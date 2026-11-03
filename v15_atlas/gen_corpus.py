#!/usr/bin/env python3
"""Generate the bench-15 atlas corpus with the local generator (free, no model call).

    python3 v15_atlas/gen_corpus.py            # 200 seeds at surface salt 0, plus 30 of them at salts 1-3

The seeds are the 43 already cached plus seeded random draws (random.Random(118)), written to
v15_atlas/corpus_seeds.txt; datasets land in .cache/datasets/v15_s<seed>_salt<salt>_full.json (git-ignored).
"""
import glob
import os
import random
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/bittensor/ditto"
GEN = f"{ROOT}/.cache/dittobench-generate-v15"
CACHE = f"{ROOT}/.cache/datasets"
N_SEEDS, N_SALTED, SALTS = 200, 30, (1, 2, 3)

cached = sorted({int(m.group(1)) for f in glob.glob(f"{CACHE}/v15_s*_salt0_full.json") if (m := re.search(r"_s(\d+)_salt0", f))})
rng = random.Random(118)
seeds = list(cached)
while len(seeds) < N_SEEDS:
    seed = rng.getrandbits(63)
    if seed not in seeds:
        seeds.append(seed)
with open(f"{ROOT}/v15_atlas/corpus_seeds.txt", "w") as out:
    out.write("\n".join(str(s) for s in seeds) + "\n")

jobs = [(s, 0) for s in seeds] + [(s, salt) for s in seeds[:N_SALTED] for salt in SALTS]


def make(job):
    seed, salt = job
    path = f"{CACHE}/v15_s{seed}_salt{salt}_full.json"
    if os.path.exists(path):
        return "cached"
    done = subprocess.run([GEN, "-bench-version", "15", "-seed", str(seed), "-run-size", "full", "-surface-salt", str(salt), "-out", path], capture_output=True, text=True)
    return "ok" if done.returncode == 0 else "FAIL " + done.stderr[-200:]


with ThreadPoolExecutor(4) as pool:
    results = list(pool.map(make, jobs))
print({r: results.count(r) for r in set(results)}, "datasets:", len(jobs))
