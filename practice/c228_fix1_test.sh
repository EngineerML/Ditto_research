#!/bin/bash
# Fix 1 (list asks: say nothing about missing items) vs v5 as uploaded: a hidden-second-item memgen copy plus normal
# memgen v6 and kinfolk v6 packs, 35 cases each, traced.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
P=.cache/miner_gens/packs/fix1; rm -rf $P; mkdir -p $P
cp .cache/miner_gens/packs/s26111-memgen-v6/pack-1.json $P/memgen-v6.json
python3 tools/hide_bindings.py .cache/miner_gens/packs/s26111-memgen-v6/pack-1.json $P/memgen-v6-hidden.json
cp "$(ls .cache/miner_gens/packs/kinfolk-v6/*.json | head -1)" $P/kinfolk-v6.json
build() {  # TAG COMMIT_OR_TREE
  rm -rf "/tmp/$1" "/tmp/replay_build/$1"; mkdir -p "/tmp/$1"
  if [ -d "$2" ]; then cp -r "$2/." "/tmp/$1/"; else git archive "$2" c228 | tar -x -C /tmp && cp -r /tmp/c228/. "/tmp/$1/" && rm -rf /tmp/c228; fi
  python3 tools/add_trace_dan0l.py "/tmp/$1" "/tmp/replay_build/$1" > /dev/null && bash tools/build_harness.sh "ditto-harness:$1" "/tmp/replay_build/$1" | tail -1
}
build c228v5t d4a1a6f
build c228fx1t c228
timeout 3600 $PY tools/generator_panel.py --packs $P --agent v5=c228v5t --agent fix1=c228fx1t --concurrency 4 2>&1 | grep -v "^20" | head -12
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
