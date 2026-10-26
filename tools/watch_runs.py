"""Watch the dan0l-vs-combined practice runs: one line per 10 finished cases, one per finished run.

    python3 tools/watch_runs.py practice/dan0l_vs_combined_full.log [START_FROM] [COMBINED_START_FROM] [RUN_GLOB]

Prints, for each block of 10 cases a traced run finishes: the lanes, paths, mean model calls,
failed model calls, empty answers and mean seconds; when a run ends, its composite, tool and
memory means; and stops when the run script prints its last line or refuses to start a run.
START_FROM skips blocks already reported (cases finished before the watch started).
"""
import collections
import glob
import json
import os
import re
import sys
import time
import urllib.request

LOG = sys.argv[1]
skip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
skip_combined = int(sys.argv[3]) if len(sys.argv) > 3 else 0
RUN_GLOB = sys.argv[4] if len(sys.argv) > 4 else "practice/*_ditto-harness-combined-trace_full"
reported: dict[str, int] = collections.defaultdict(int)
seen_lines = 0


def say(text: str) -> None:
    print(text, flush=True)


def blocks(run: str) -> None:
    path = os.path.join(run, "trace.jsonl")
    if not os.path.isfile(path):
        return
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    name = "dan0l" if "dan0l" in run else "combined"
    floor = skip if name == "dan0l" else skip_combined
    done = reported[run] or (floor // 10) * 10
    while len(rows) - done >= 10:
        b = rows[done:done + 10]
        lanes = collections.Counter((t.get("lane") or "?").split(":")[0] for t in b)
        paths = collections.Counter(t.get("path") or "-" for t in b)
        errors = sum(1 for t in b for c in t["calls"] if str(c["finish"]).startswith("llm-error"))
        empty = sum(1 for t in b if not (t.get("final_text") or "").strip())
        say(f"{name} {done + 1}-{done + 10}: lanes rec {lanes.get('records', 0)} act {lanes.get('action', 0)} | "
            f"paths {dict(paths)} | calls/q {sum(len(t['calls']) for t in b) / 10:.1f} | failed calls {errors} | empty {empty} | "
            f"avg {sum(t.get('seconds', 0) for t in b) / 10:.0f}s")
        done += 10
    reported[run] = done


scored: dict[str, int] = collections.defaultdict(int)
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def scores(run: str) -> None:
    """Blocks of 10 graded cases from the live scorer's partial results, in the order it graded them."""
    log = os.path.join(run, "scorer.log")
    if not os.path.isfile(log):
        return
    text = open(log, encoding="utf-8", errors="ignore").read()
    port = re.search(r"practice validator\) listening on :(\d+)", text)
    run_id = re.findall(r"GET /v1/runs/([0-9a-f-]+)", text)
    if not port or not run_id:
        return
    try:
        with NO_PROXY.open(f"http://127.0.0.1:{port.group(1)}/v1/runs/{run_id[-1]}", timeout=10) as resp:
            partial = json.load(resp).get("partial") or []
    except (OSError, ValueError):
        return
    name = "dan0l" if "dan0l" in run else "combined"
    floor = skip if name == "dan0l" else skip_combined
    done = scored[run] or (floor // 10) * 10
    while len(partial) - done >= 10:
        b = partial[done:done + 10]
        lost = [f"{c['category']}={c['score']:.2g}" for c in b if (c.get("score") or 0) < 0.999]
        say(f"{name} graded {done + 1}-{done + 10}: mean {sum(c.get('score') or 0 for c in b) / 10:.3f} | lost points {len(lost)}"
            + (f" ({', '.join(lost)})" if lost else ""))
        done += 10
    scored[run] = done


while True:
    lines = open(LOG, encoding="utf-8").read().splitlines() if os.path.isfile(LOG) else []
    for line in lines[seen_lines:]:
        if re.search(r"^=====|composite:|tool_mean:|memory_mean:|^after |balance under|Traceback|Error", line):
            say("RUN " + line.strip())
    seen_lines = len(lines)
    for run in sorted(glob.glob("practice/*_ditto-harness-dan0l-v24-trace_full") + glob.glob(RUN_GLOB)):
        if os.path.getmtime(run) > time.time() - 6 * 3600:
            blocks(run)
            scores(run)
    if any(l.startswith("===== done") or "balance under" in l for l in lines):
        break
    time.sleep(20)
