#!/bin/bash
# referring_turns on bauni v6 packs 1-3 (105 cases), traced image c228rtt (built by practice/c228_rt_build.sh).
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
bash practice/c228_rt_build.sh | tail -3
# free mock pass first: any harness error stops the paid run
timeout 1200 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/bauni6-p1 --agent rt=c228rtt --concurrency 4 --mock 2>&1 | grep -v "^20" | tail -3
m=$(ls -td practice/generator/2026*Z-mock | head -1)
if grep -q Traceback $m/trace/*/rt/harness.log 2>/dev/null; then grep -h -A3 -m1 Error $m/trace/*/rt/harness.log | head -8; echo "mock run hit an error, not starting"; exit 1; fi
grep -h -o "next turns that speak of someone by a phrase[^\"]*" $m/trace/*/rt/trace.jsonl | sort | uniq -c | head -5
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/bauni6 --agent rt=c228rtt --concurrency 4 2>&1 | grep -v "^20" | tail -4
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
for r in $(ls $d/trace); do
  python3 - "$d" "$r" <<'P'
import json, sys, collections
d, r = sys.argv[1], sys.argv[2]
pack = json.load(open(f"{d}/packs/{r.rsplit('-r', 1)[0]}.json"))
byq = {c["question"]: c for c in pack["cases"]}
DECL = ("no record", "couldn't find", "couldn’t find", "unknown", "don't have", "not recorded")
dist, tot, n, fired = collections.Counter(), 0.0, 0, 0
for line in open(f"{d}/trace/{r}/rt/trace.jsonl"):
    t = json.loads(line)
    c = byq[t["user_input"]]
    fired += any("speak of someone by a phrase" in str(e) for e in t.get("events") or [])
    reply = (t.get("final_text") or "").lower()
    got = [i for i in c["answer_items"] if i.lower() in reply]
    bad = [x for x in c["distractor_answers"] if x.lower() in reply]
    dec = any(w in reply for w in DECL)
    s = 0.0 if bad or dec else len(got) / len(c["answer_items"])
    tot += s; n += 1
    k = "distractor" if bad else f"{len(got)}/2" + (" +decline" if dec else "")
    dist[k] += 1
    if s < 1:
        print("   ", c["id"], k, "|", (t.get("final_text") or "").replace("\n", " ")[:140])
print(r, f"approx mean {tot / n:.2f} over {n}", dict(dist), "fired", fired)
P
done
