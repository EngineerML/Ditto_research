"""Top of the generator board and the agent leaderboard in every live/ snapshot, oldest first (data only).
    python3 -I live/board_trend.py
"""
import glob, json, os


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


print("== generator board: top 6 per snapshot (score / discriminating cases)")
for snap in sorted(glob.glob("/home/bittensor/ditto/live/2026-*")):
    gb = load(f"{snap}/generator_board.json")
    if not gb or not gb.get("entries"):
        continue
    rows = sorted(gb["entries"], key=lambda e: -(e.get("score") or 0))[:6]
    print(os.path.basename(snap), " | ".join(f"{e.get('name')} v{e.get('version')} {e.get('score') or 0:.3f}/{e.get('discriminating_cases')}"
                                             for e in rows))

print("\n== agent leaderboard: bench, top 5 composite (effective) and average run cost")
for snap in sorted(glob.glob("/home/bittensor/ditto/live/2026-*")):
    lb = load(f"{snap}/public_leaderboard.json")
    if not lb or not lb.get("entries"):
        continue
    rows = sorted(lb["entries"], key=lambda e: -((e.get("effective_composite") or e.get("composite") or 0)))[:5]
    def cost(e):
        c = e.get("average_run_cost_microusd")
        return f" ${c/1e6:.2f}" if c else ""
    print(os.path.basename(snap), f"bench {lb.get('scoring_bench_version')}",
          " | ".join(f"{e.get('agent_name')} v{e.get('agent_version')} {(e.get('effective_composite') or e.get('composite') or 0):.3f}{cost(e)}"
                     for e in rows))

latest = sorted(glob.glob("/home/bittensor/ditto/live/2026-*"))[-1]
gb = load(f"{latest}/generator_board.json")
print(f"\n== {os.path.basename(latest)} generator board, all entries, with recent round scores")
for e in sorted(gb["entries"], key=lambda e: -(e.get("score") or 0)):
    rec = [r.get("score") for r in (e.get("recent") or [])][-8:]
    print(f"{e.get('score') or 0:.3f} disc {e.get('discriminating_cases')} {e.get('name')} v{e.get('version')} {e['submission_id'][:8]} "
          f"rounds {e.get('rounds_in_window')} first {str(e.get('first_seen'))[:10]} recent {[round(x or 0, 2) for x in rec]}")
lb = load(f"{latest}/public_leaderboard.json")
print(f"\n== {os.path.basename(latest)} agent leaderboard top 15")
for e in sorted(lb["entries"], key=lambda e: -((e.get("effective_composite") or e.get("composite") or 0)))[:15]:
    c = e.get("average_run_cost_microusd")
    print(f"{(e.get('effective_composite') or 0):.3f} comp {(e.get('composite') or 0):.3f} eff {e.get('efficiency_factor')} "
          f"cost {('$%.2f' % (c/1e6)) if c else '-'} {e.get('agent_name')} v{e.get('agent_version')} {e['agent_id'][:8]} "
          f"uid {e.get('miner_uid')} family {e.get('submission_family')}")
