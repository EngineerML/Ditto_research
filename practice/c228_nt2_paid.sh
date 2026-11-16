#!/bin/bash
# number_threads port + asked-name filter in the tied-names view: traced image c228nt2t, staged-records-v4 packs 1-3 (105 cases).
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
rm -rf /tmp/c228nt2t /tmp/replay_build/c228nt2t; mkdir -p /tmp/c228nt2t
cp -r c228/. /tmp/c228nt2t/
python3 tools/add_trace_dan0l.py /tmp/c228nt2t /tmp/replay_build/c228nt2t > /dev/null && bash tools/build_harness.sh ditto-harness:c228nt2t /tmp/replay_build/c228nt2t | tail -1
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/sr4 --agent nt2=c228nt2t --concurrency 4 2>&1 | grep -v "^20" | tail -3
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
for r in $(ls $d/trace); do
  python3 - "$d" "$r" <<'P'
import json, sys, collections
d, r = sys.argv[1], sys.argv[2]
pack = json.load(open(f"{d}/packs/{r.rsplit('-r', 1)[0]}.json"))
byq = {c["question"]: c for c in pack["cases"]}
DECL = ("no record", "couldn't find", "couldn’t find", "unknown", "don't have", "not recorded")
dist, tot, n = collections.Counter(), 0.0, 0
for line in open(f"{d}/trace/{r}/nt2/trace.jsonl"):
    t = json.loads(line)
    c = byq[t["user_input"]]
    reply = (t.get("final_text") or "").lower()
    got = [i for i in c["answer_items"] if i.lower() in reply]
    bad = [x for x in c["distractor_answers"] if x.lower() in reply]
    dec = any(w in reply for w in DECL)
    s = 0.0 if bad or dec else len(got) / len(c["answer_items"])
    tot += s; n += 1
    dist["distractor" if bad else f"{len(got)}/2" + (" +decline" if dec else "")] += 1
print(r, f"approx mean {tot / n:.2f} over {n}", dict(dist))
P
done
