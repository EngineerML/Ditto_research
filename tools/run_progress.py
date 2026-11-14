"""Live progress of a local practice run: graded accuracy and spend, per block of N finished cases.

Reads the scorer's own run status (GET /v1/runs/<id> on the local scorer, found in the run folder's scorer.log) for the
graded cases, and the practice trace (trace.jsonl, one line per finished case) for the model tokens each case used.
Cost is priced at the bench model's OpenRouter list price (gpt-oss-20b: $0.03 / M prompt, $0.14 / M completion by
default; override with --in-price / --out-price).

    .venv/bin/python tools/run_progress.py [RUN_DIR] [--block 10]
"""
import argparse
import glob
import json
import re
import urllib.request
from collections import defaultdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--block", type=int, default=10)
    ap.add_argument("--in-price", type=float, default=0.03)
    ap.add_argument("--out-price", type=float, default=0.14)
    ap.add_argument("--dump", action="store_true", help="print the status keys (debug)")
    args = ap.parse_args()
    run = args.run or sorted(glob.glob("/home/bittensor/ditto/practice/2026*_full"))[-1]
    log = open(f"{run}/scorer.log").read()
    port = re.search(r"dittobench-api[^\n]*listening on [^\n]*?:(\d+)", log)
    run_id = re.findall(r"GET /v1/runs/([0-9a-f-]{36})", log)[-1]
    ports = re.findall(r"(?:127\.0\.0\.1|0\.0\.0\.0|localhost):(\d+)", log)
    status = None
    for p in dict.fromkeys(([port.group(1)] if port else []) + ports):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{p}/v1/runs/{run_id}", timeout=5) as r:
                status = json.loads(r.read())
                break
        except Exception:
            continue
    if status is None:
        print("scorer not reachable (run finished?); see report.json")
        return 1
    if args.dump:
        print(json.dumps({k: (v if not isinstance(v, (list, dict)) else type(v).__name__) for k, v in status.items()}, indent=1))
        print(json.dumps(status.get("progress"))[:800])
        print(json.dumps(status.get("partial"))[:1500])
    partial = status.get("partial") or []
    cases = partial if isinstance(partial, list) else (partial.get("per_case") or partial.get("cases") or [])
    if isinstance(cases, dict):
        cases = list(cases.values())
    tokens = {}
    for line in open(f"{run}/trace.jsonl"):
        t = json.loads(line)
        pt = sum((c.get("prompt_tokens") or (c.get("usage") or {}).get("prompt_tokens") or 0) for c in t.get("calls", []))
        ct = sum((c.get("completion_tokens") or (c.get("usage") or {}).get("completion_tokens") or 0) for c in t.get("calls", []))
        tokens[t.get("case_id")] = (pt, ct, len(t.get("calls", [])))
    prog = status.get("progress") or {}
    print(f"run {run.split('/')[-1]}  status {status.get('status')}  progress {prog}")
    done = [c for c in cases if c.get("score") is not None]
    print(f"graded {len(done)}   traced {len(tokens)}")
    print(f"{'cases':>9} {'acc(block)':>10} {'acc(all)':>9} {'tool':>6} {'mem':>6} {'prompt':>9} {'compl':>8} {'calls':>5} {'$block':>7} {'$all':>7}")
    tot = defaultdict(float)
    keys = list(tokens)
    for start in range(0, max(len(done), len(keys)), args.block):
        blk = done[start:start + args.block]
        tk = [tokens[k] for k in keys[start:start + args.block]]
        pt, ct, calls = (sum(x[i] for x in tk) for i in range(3))
        cost = pt / 1e6 * args.in_price + ct / 1e6 * args.out_price
        tot["cost"] += cost
        tot["n"] += len(blk)
        tot["s"] += sum(c["score"] for c in blk)
        tools = [c["score"] for c in blk if (c.get("kind") or "").startswith("tool")]
        mems = [c["score"] for c in blk if (c.get("kind") or "").startswith("mem")]
        acc = sum(c["score"] for c in blk) / len(blk) if blk else float("nan")
        print(f"{start + 1:>4}-{start + max(len(blk), len(tk)):<4} {acc:>10.3f} {tot['s'] / max(1, tot['n']):>9.3f} "
              f"{(sum(tools) / len(tools)) if tools else float('nan'):>6.2f} {(sum(mems) / len(mems)) if mems else float('nan'):>6.2f} "
              f"{pt:>9,} {ct:>8,} {calls:>5} {cost:>7.3f} {tot['cost']:>7.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
