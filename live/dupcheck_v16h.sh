#!/bin/bash
# Copy-gate check of a packed submission against every released agent held locally, plus a list of released agents not held.
set -e
cd /home/bittensor/ditto
PKG=${1:-practice/submission_d42c_v16h.tgz}
T=$(mktemp -d); tar -xzf "$PKG" -C "$T"
echo "== released on platform (activity, latest 200) but not in released/ =="
python3 - <<'PY'
import json, glob, os
act = json.load(open(sorted(glob.glob("live/2026-11-12T*/public_activity_limit_200.json"))[-1]))["entries"]
have = {os.path.basename(p).rsplit("_", 1)[-1] for p in glob.glob("released/*_*")}
for e in act:
    rel = e.get("artifact_release") or {}
    if rel.get("status") not in ("embargoed", "unavailable", None):
        tag = "HAVE" if e["agent_id"][:8] in have else "MISSING"
        print(tag, e["name"], "v", e["version"], e["agent_id"][:8], rel.get("status"), rel.get("released_at") or rel.get("release_at"))
PY
echo "== fingerprint vs every released tree =="
for r in released/*/src; do
  .venv/bin/python tools/anticopy_check.py "$r" "$T" 2>/dev/null | tail -1 | sed "s#^$T#$(basename $(dirname $r))#"
done | sort -t' ' -k4 -r | awk '{print}' 
rm -rf "$T"
