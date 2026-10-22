"""Summarize a live/YYYY-MM-DD snapshot: reward split, champion defense, top of the leaderboard, fee.

    python3 tools/summarize.py live/2026-10-22
"""

import collections
import json
import sys
from pathlib import Path


def main(day: Path) -> None:
    lb = json.load(open(day / "public_leaderboard.json"))
    em = lb["emissions"]
    print(f"bench v{lb['current_bench_version']}, {len(lb['entries'])} entries, generated {lb['generated_at']}")
    print("rank shares:", em.get("rank_shares"), "| margin:", em.get("margin"), "| dethrone z:", em.get("dethrone_z"))
    print("paid now:")
    for r in em.get("recipients", []):
        print(f"  {r['role']:9s} {r['share_of_miner_pool']:<5} raw rank {r.get('raw_rank')}  {r['miner_hotkey'][:12]}")
    d = em.get("champion_defense") or {}
    if d:
        print(f"champion defense: best challenger lead {d['challenger_lead']:.4f}, needs {d['required_lead']:.4f} "
              f"-> score to beat {d['required_score']:.4f}")

    print(f"\n{'rk':>3} {'uid':>4} {'name':18s} {'comp':>6} {'±se':>6} {'tool':>6} {'mem':>6} first seen")
    for e in lb["entries"][:15]:
        print(f"{e['rank']:>3} {e.get('miner_uid')!s:>4} {str(e.get('agent_name'))[:18]:18s} {e['composite']:>6.4f} "
              f"{(e.get('composite_stderr') or 0):>6.4f} {e.get('tool_mean') or 0:>6.3f} "
              f"{e.get('memory_mean') or 0:>6.3f} {str(e.get('first_seen'))[:16]}")
    champ = next((e for e in lb["entries"] if e["agent_id"] == em.get("champion_agent_id")), None)
    if champ:
        print(f"\nchampion: uid {champ.get('miner_uid')} '{champ.get('agent_name')}' {champ['composite']:.4f}, "
              f"crown since {str(champ.get('crown_first_seen'))[:16]}")
    owners = collections.Counter(e["miner_hotkey"] for e in lb["entries"])
    print("distinct hotkeys:", len(owners))

    price = json.load(open(day / "upload_eval-pricing.json"))
    print(f"eval fee: {int(price['amount_rao']) / 1e9} TAO")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
