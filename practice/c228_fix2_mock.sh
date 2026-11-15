#!/bin/bash
# Fix 2 (long-record nickname ties): build traced image of the working tree, free mock on the 5FqQq9 packs,
# then count cases whose model input carries the "is called" advisory line naming the case's nickname.
cd /home/bittensor/ditto || exit 1
python3 -m py_compile c228/app/memory/coverage.py || exit 1
rm -rf /tmp/c228fx2t /tmp/replay_build/c228fx2t; mkdir -p /tmp/c228fx2t
cp -r c228/. /tmp/c228fx2t/
python3 tools/add_trace_dan0l.py /tmp/c228fx2t /tmp/replay_build/c228fx2t > /dev/null && bash tools/build_harness.sh ditto-harness:c228fx2t /tmp/replay_build/c228fx2t | tail -1
timeout 1500 .venv/bin/python tools/generator_panel.py --mock --packs .cache/miner_gens/packs/fq-v2 \
  --agent v5=c228v5t --agent fix2=c228fx2t --concurrency 6 > /tmp/c228_fix2_mock.log 2>&1
echo "mock exit $?"; grep -ci traceback /tmp/c228_fix2_mock.log
d=$(ls -td practice/generator/*-mock | head -1)
python3 - "$d" <<'P'
import json, glob, sys, re
for f in sorted(glob.glob(sys.argv[1] + "/trace/*/*/trace.jsonl")):
    n = hit = 0
    for line in open(f):
        t = json.loads(line)
        n += 1
        blob = json.dumps(t.get("calls", []))
        hit += "says they are called" in blob
    print(f.split("/")[-3], f.split("/")[-2], "cases", n, "with a called-name line", hit)
P
