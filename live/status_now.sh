#!/bin/bash
# Fresh snapshot, then: agent leaderboard top 12 + ours, released (downloadable) agents, generator board, released generator sources.
cd /home/bittensor/ditto || exit 1
d=$(bash live/fetch_now.sh | tail -1)
python3 - "$d" <<'P'
import json, sys
d = sys.argv[1] + "/"
lb = json.load(open(d + "public_leaderboard.json"))["entries"]
print("AGENT LEADERBOARD")
for i, e in enumerate(lb):
    if i < 12 or e.get("agent_name") == "overhorizoner":
        keys = [k for k in ("composite", "score", "dueling_score", "provisional_composite") if e.get(k) is not None]
        print(f"  {i+1:3} {e.get('agent_name')} v{e.get('agent_version')} {e['agent_id'][:8]} " + " ".join(f"{k}={e[k]:.4f}" for k in keys if isinstance(e[k], (int, float))))
act = json.load(open(d + "public_activity_limit_200.json"))["entries"]
print("RELEASED AGENTS (downloadable)")
for e in act:
    r = e.get("artifact_release") or {}
    if r.get("download_available") or r.get("status") in ("released", "available", "public"):
        print(f"  {e['name']} v{e['version']} {e['agent_id'][:8]} avail {r.get('available_at')} bench {r.get('bench_version')}")
print("UPCOMING / EMBARGOED top agents")
for e in act:
    r = e.get("artifact_release") or {}
    if r.get("status") == "embargoed" and (e.get("provisional_composite") or 0) > 0.8:
        print(f"  {e['name']} v{e['version']} {e['agent_id'][:8]} prov {e['provisional_composite']:.4f} avail {r.get('available_at')}")
ours = [e for e in act if e["name"] == "overhorizoner"]
for e in ours[:3]:
    print("  OURS", {k: e.get(k) for k in ("version", "status", "provisional_composite", "last_scored_at")})
print("GENERATOR BOARD")
for g in json.load(open(d + "generator_board.json"))["entries"][:10]:
    print(f"  {g['score']:.3f} {g.get('name')} v{g.get('version')} disc={g.get('discriminating_cases')} round {g.get('round_index')} {g['submission_id'][:8]}")
P
echo "$d"
