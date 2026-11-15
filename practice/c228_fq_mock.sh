#!/bin/bash
# Free mock: 5FqQq9 v2 packs against vanilla crown-v228 (traced), v5 as uploaded and v5+fix1.
# Shows per family whether the nickname card and the update reached the model.
cd /home/bittensor/ditto || exit 1
if ! docker image inspect ditto-harness:crown228t > /dev/null 2>&1; then
  rm -rf /tmp/crown228t /tmp/replay_build/crown228t; mkdir -p /tmp/crown228t
  cp -r released/crown-v228-v1_673386d0/src/. /tmp/crown228t/
  python3 tools/add_trace_dan0l.py /tmp/crown228t /tmp/replay_build/crown228t > /dev/null && bash tools/build_harness.sh ditto-harness:crown228t /tmp/replay_build/crown228t | tail -1
fi
timeout 1500 .venv/bin/python tools/generator_panel.py --mock --packs .cache/miner_gens/packs/fq-v2 \
  --agent crown=crown228t --agent v5=c228v5t --agent fix1=c228fx1t --concurrency 6 > /tmp/c228_fq_mock.log 2>&1
echo "mock exit $?"
grep -v "^20" /tmp/c228_fq_mock.log | tail -40
