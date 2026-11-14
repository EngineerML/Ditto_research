"""Model tokens and cost per case from practice traces, per generator pack (or per datagen run), for each agent.

Cost is priced at list rates (--in-price / --out-price per million tokens, gpt-oss-20b defaults) times --scale,
the ratio of what OpenRouter actually charged to the list-price estimate on a local run (1.8 on 2026-11-14).

    .venv/bin/python tools/case_cost.py TRACE_GLOB [TRACE_GLOB ...]
"""
import argparse
import glob
import json
import statistics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("globs", nargs="+")
    ap.add_argument("--in-price", type=float, default=0.03)
    ap.add_argument("--out-price", type=float, default=0.14)
    ap.add_argument("--scale", type=float, default=1.8)
    args = ap.parse_args()
    print(f"{'trace':58} {'n':>4} {'calls':>5} {'prompt/case':>11} {'max prompt':>10} {'$/case':>8} {'max $':>7} {'$ x175':>7}")
    for pattern in args.globs:
        for f in sorted(glob.glob(pattern)):
            rows = []
            for line in open(f):
                t = json.loads(line)
                calls = t.get("calls") or []
                pt = sum(c.get("prompt_tokens") or 0 for c in calls)
                ct = sum(c.get("completion_tokens") or 0 for c in calls)
                rows.append((pt, ct, len(calls)))
            if not rows:
                continue
            cost = [(pt / 1e6 * args.in_price + ct / 1e6 * args.out_price) * args.scale for pt, ct, _ in rows]
            name = "/".join(f.split("/")[-4:-1])[-58:]
            print(f"{name:58} {len(rows):>4} {statistics.mean(r[2] for r in rows):>5.1f} {statistics.mean(r[0] for r in rows):>11,.0f} "
                  f"{max(r[0] for r in rows):>10,} {statistics.mean(cost):>8.5f} {max(cost):>7.4f} {statistics.mean(cost) * 175:>7.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
