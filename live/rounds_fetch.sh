#!/bin/bash
# Fetch public generator round details (panel, columns, counts) into live/rounds/.
#   bash live/rounds_fetch.sh 26128 26129 ...
source /etc/profile.d/zz-proxy.sh
mkdir -p /home/bittensor/ditto/live/rounds
cd /home/bittensor/ditto/live/rounds || exit 1
rm -f r.json
for r in "$@"; do
  curl -s --max-time 30 "https://platform-api.heyditto.ai/api/v1/generator/rounds/$r" -o "r$r.json"
done
python3 - "$@" <<'P'
import json, sys
for r in sys.argv[1:]:
    try:
        d = json.load(open(f"r{r}.json"))
    except Exception as e:
        print(r, "bad", e); continue
    s = d.get("summary", {})
    print(f"round {r} status={s.get('status')} panel={s.get('panel_size')} bench={[c.get('grading_bench_version') for c in d.get('columns', [])][:1]}")
    for c in d.get("columns", []):
        print(f"   {str(c.get('name'))[:14]:14} v{c.get('version')} score={c.get('score') or 0:.3f} disc={c.get('discriminating')} triv={c.get('trivial')} uns={c.get('unsolved')} dup={c.get('duplicate')}")
    extra = [k for k in d if k not in ("summary", "columns")]
    if extra and r == sys.argv[1]:
        for k in extra:
            print("  key", k, json.dumps(d[k])[:600])
P
