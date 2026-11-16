#!/bin/bash
# bauni v6 (season 26126 c2, released 2026-11-16) pack 1, 35 cases: our 37bd158 tree (traced c228nt2t) vs released dan0l v59 (traced d59t).
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
mkdir -p .cache/miner_gens/packs/bauni6-p1
[ -e .cache/miner_gens/packs/bauni6-p1/pack-1.json ] || cp .cache/miner_gens/packs/bauni6/pack-1.json .cache/miner_gens/packs/bauni6-p1/
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/bauni6-p1 --agent nt2=c228nt2t --agent d59=d59t --concurrency 4 2>&1 | grep -v "^20" | tail -6
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
python3 practice/sr4_score.py $d pack-1-r0 nt2 d59
