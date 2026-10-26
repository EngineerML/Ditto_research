"""Watch subset A/B runs: one line per 10 graded questions, against the base full run's scores.

    python3 tools/watch_subset.py LOG BASE_SEED_A=RUN_DIR [BASE_SEED_B=RUN_DIR ...]

Follows the newest *_full_rerun folder while LOG grows. For each block of 10 questions the live
scorer has graded: the block's mean, the base run's mean on the same questions, and the questions
that differ (gained or lost). Stops when LOG prints "===== all done" (with WATCH_UNTIL=done, at
the first "===== done"). RUN_GLOB=practice/*_<tag>_full follows a full run instead.
"""
import glob
import json
import os
import re
import sys
import time
import urllib.request

LOG = sys.argv[1]
FINAL = os.environ.get("WATCH_UNTIL", "all done")  # "done" stops at the first finished ab_subset call
RUN_GLOB = os.environ.get("RUN_GLOB", "practice/*_full_rerun")  # e.g. practice/*_full for a full run
BASES = {}
for spec in sys.argv[2:]:
    seed, run = spec.split("=", 1)
    BASES[seed] = {c["case_id"]: c for c in json.load(open(os.path.join(run, "report.json")))["report"]["per_case"]}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
reported: dict[str, int] = {}


def partial(run: str) -> list[dict]:
    text = open(os.path.join(run, "scorer.log"), errors="ignore").read()
    port = re.search(r"practice validator\) listening on :(\d+)", text)
    rid = re.findall(r"GET /v1/runs/([0-9a-f-]+)", text)
    if not port or not rid:
        return []
    try:
        with OPENER.open(f"http://127.0.0.1:{port.group(1)}/v1/runs/{rid[-1]}", timeout=10) as resp:
            return json.load(resp).get("partial") or []
    except (OSError, ValueError):
        return []


def seed_of(run: str) -> str:
    text = open(os.path.join(run, "scorer.log"), errors="ignore").read()
    m = re.search(r"seed=(\d+)", text)
    return m.group(1) if m else ""


while True:
    log = open(LOG, encoding="utf-8").read() if os.path.isfile(LOG) else ""
    runs = sorted(glob.glob(RUN_GLOB), key=os.path.getmtime)
    if runs and os.path.getmtime(runs[-1]) > time.time() - 3 * 3600:
        run = runs[-1]
        rows = partial(run)
        base = BASES.get(seed_of(run), {})
        label = re.search(r"ditto-harness-([\w-]+?)_full", run).group(1)
        done = reported.get(run, 0)
        while len(rows) - done >= 10 or (rows and len(rows) > done and os.path.isfile(os.path.join(run, "report.json"))):
            block = rows[done:done + 10]
            mean = sum(c["score"] for c in block) / len(block)
            known = [c for c in block if c["case_id"] in base]
            base_mean = sum(base[c["case_id"]]["score"] for c in known) / len(known) if known else float("nan")
            diffs = [f"{'+' if c['score'] > base[c['case_id']]['score'] else '-'}{c['category']}"
                     for c in known if abs(c["score"] - base[c["case_id"]]["score"]) > 0.01]
            total = sum(c["score"] for c in rows[:done + len(block)]) / (done + len(block))
            print(f"{label} {done + 1}-{done + len(block)}: mean {mean:.3f} (so far {total:.3f}) | base run {base_mean:.3f}"
                  + (f" | changed: {', '.join(diffs)}" if diffs else ""), flush=True)
            done += len(block)
        reported[run] = done
    if "===== all done" in log or (FINAL == "done" and re.search(r"^===== done", log, re.M)) or "not starting" in log:
        break
    time.sleep(20)
