"""How much does each leaderboard entry lose to the integrity gates?

composite = (0.5*tool_mean + 0.5*memory_mean) x gates, so gates = composite / mean(tool, memory).
Also shows the reported run cost, a proxy for tokens spent.

    python3 tools/gate_factor.py live/2026-10-22
"""

import json
import statistics
import sys
from pathlib import Path


def main(day: Path) -> None:
    lb = json.load(open(day / "public_leaderboard.json"))
    rows = []
    for e in lb["entries"]:
        tool, mem, comp = e.get("tool_mean"), e.get("memory_mean"), e.get("composite")
        if not (tool and mem and comp):
            continue
        base = (tool + mem) / 2
        rows.append((comp, base, comp / base, e))
    rows.sort(key=lambda r: -r[0])
    print(f"{'uid':>4} {'name':16s} {'comp':>6} {'tool':>6} {'mem':>6} {'base':>6} {'gates':>6} {'loss':>6} {'$/run':>6}")
    for comp, base, factor, e in rows[:20]:
        cost = (e.get("average_run_cost_microusd") or 0) / 1e6
        print(f"{e.get('miner_uid')!s:>4} {str(e.get('agent_name'))[:16]:16s} {comp:>6.4f} {e['tool_mean']:>6.3f} "
              f"{e['memory_mean']:>6.3f} {base:>6.4f} {factor:>6.3f} {base - comp:>6.4f} {cost:>6.2f}")
    factors = [r[2] for r in rows[:15]]
    bases = [r[1] for r in rows[:15]]
    print(f"\ntop 15: gate factor median {statistics.median(factors):.3f} (min {min(factors):.3f}, max {max(factors):.3f}); "
          f"base (pre-gate) median {statistics.median(bases):.4f}, max {max(bases):.4f}")
    best_base = max(rows[:15], key=lambda r: r[1])
    print(f"highest pre-gate base: uid {best_base[3].get('miner_uid')} {best_base[1]:.4f} -> composite {best_base[0]:.4f} "
          f"(gates {best_base[2]:.3f})")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
