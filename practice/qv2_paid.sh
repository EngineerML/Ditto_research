#!/bin/bash
# querverweis v2 (predecessor of the always-pinned v3) pack 1, 35 cases: our 57853f5 tree (traced c228rtt).
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
mkdir -p .cache/miner_gens/packs/qv2-p1
[ -e .cache/miner_gens/packs/qv2-p1/pack-1.json ] || cp .cache/miner_gens/packs/qv2/pack-1.json .cache/miner_gens/packs/qv2-p1/
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/qv2-p1 --agent rt=c228rtt --concurrency 4 2>&1 | grep -v "^20" | tail -4
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
python3 practice/list_tally.py $d rt
