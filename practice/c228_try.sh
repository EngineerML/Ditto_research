#!/bin/bash
# Build a traced image from the c228 tree, run a free mock pass (stop on any harness error), then the paid run and the
# grader-normalised list tally.
#   bash practice/c228_try.sh TAG PACKDIR
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
TAG=$1; PACKS=$2; PY=.venv/bin/python
$PY -m py_compile c228/app/*.py c228/app/memory/*.py && echo compiled || exit 1
rm -rf /tmp/$TAG /tmp/replay_build/$TAG; mkdir -p /tmp/$TAG
cp -r c228/. /tmp/$TAG/
python3 tools/add_trace_dan0l.py /tmp/$TAG /tmp/replay_build/$TAG > /dev/null && bash tools/build_harness.sh ditto-harness:$TAG /tmp/replay_build/$TAG | tail -1
timeout 1200 $PY tools/generator_panel.py --packs $PACKS --agent a=$TAG --concurrency 4 --mock 2>&1 | grep -v "^20" | tail -2
m=$(ls -td practice/generator/2026*Z-mock | head -1)
if grep -q Traceback $m/trace/*/a/harness.log 2>/dev/null; then grep -h -B2 -m1 Error $m/trace/*/a/harness.log | head -8; echo "mock run hit an error, not starting"; exit 1; fi
echo "mock clean: $m"
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs $PACKS --agent a=$TAG --concurrency 4 2>&1 | grep -v "^20" | tail -3
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
python3 practice/list_tally.py $d a
