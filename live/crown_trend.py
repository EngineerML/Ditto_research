"""Agent-side trend from every live/ snapshot: crowns per day, crowned owners, and leaderboard top-10 composite/cost.
    python3 -I live/crown_trend.py
"""
import collections, glob, json, os

crowns = {}
lb_rows = []
for snap in sorted(glob.glob("/home/bittensor/ditto/live/2026-*")):
    try:
        act = json.load(open(f"{snap}/public_activity_limit_200.json"))
        for e in act["entries"]:
            r = e.get("artifact_release") or {}
            if r.get("crowned_at"):
                crowns[e["agent_id"]] = (r["crowned_at"], e["name"], e["version"], e.get("miner_uid"), r.get("bench_version"))
    except Exception:
        pass
    try:
        lb = json.load(open(f"{snap}/public_leaderboard.json"))
        top = sorted(lb["entries"], key=lambda e: -(e.get("composite") or 0))[:10]
        comps = [e.get("composite") or 0 for e in top]
        costs = [e["average_run_cost_microusd"] / 1e6 for e in top if e.get("average_run_cost_microusd")]
        lb_rows.append((os.path.basename(snap)[:10], lb.get("scoring_bench_version"), max(comps), sum(comps) / len(comps),
                        sum(costs) / len(costs) if costs else None, len({e.get("miner_uid") for e in top})))
    except Exception:
        pass

print("== crowns per day (bench) and crowned names, from activity snapshots")
by_day = collections.defaultdict(list)
for aid, (t, name, ver, uid, bench) in crowns.items():
    by_day[t[:10]].append(f"{name} v{ver}")
for day in sorted(by_day):
    print(f"{day} {len(by_day[day]):>3}  {', '.join(sorted(by_day[day]))[:220]}")

print("\n== leaderboard top 10 per day (last snapshot of the day): bench, best, mean, mean cost $, distinct uids")
last = {}
for row in lb_rows:
    last[row[0]] = row
for day, row in sorted(last.items()):
    print(f"{day} bench {row[1]} best {row[2]:.3f} mean {row[3]:.3f} cost {row[4] and round(row[4], 2)} uids {row[5]}")
