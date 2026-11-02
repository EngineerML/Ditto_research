"""Poll the local scorer's run status and print one line per 10 graded questions (memory-only mean too).

    python3 practice/gates/per10.py SCORER_PORT RUN_ID [START]
"""
import json
import sys
import time
import urllib.request

URL = f"http://127.0.0.1:{sys.argv[1]}/v1/runs/{sys.argv[2]}"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
FINAL = {"done", "failed", "error", "cancelled", "canceled"}
done = int(sys.argv[3]) if len(sys.argv) > 3 else 0
total_seen = []
first = True
while True:
    try:
        status = json.load(opener.open(URL, timeout=10))
    except Exception as exc:
        print(f"scorer not answering ({exc}); run finished or stopped", flush=True)
        break
    parts = status.get("partial") or []
    final = status.get("status") in FINAL
    if first:
        total_seen.extend(parts[:done])
        first = False
    while len(parts) >= done + 10 or (final and len(parts) > done):
        batch = parts[done:done + 10]
        total_seen.extend(batch)
        scores = [p.get("score") or 0 for p in batch]
        kinds = {}
        for p in batch:
            kinds.setdefault(p.get("kind"), []).append(p.get("score") or 0)
        split = ", ".join(f"{k} {sum(v):.1f}/{len(v)}" for k, v in sorted(kinds.items()))
        misses = [f"{p.get('category')}={p.get('score') or 0:.2f}" for p in batch if (p.get("score") or 0) < 1]
        allscores = [p.get("score") or 0 for p in total_seen]
        memory = [p.get("score") or 0 for p in total_seen if p.get("kind") == "memory"]
        mem_mean = f" | memory mean {sum(memory) / len(memory):.3f} over {len(memory)}" if memory else ""
        print(f"Q{done + 1}-{done + len(batch)}: {sum(scores):.2f}/{len(batch)} ({split}){mem_mean} | all mean {sum(allscores) / len(allscores):.3f}"
              + (f" | below 1: {', '.join(misses)}" if misses else ""), flush=True)
        done += len(batch)
    if final and done >= len(parts):
        print(f"run status: {status.get('status')}", flush=True)
        break
    time.sleep(15)
