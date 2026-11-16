#!/bin/bash
# referring_turns (bauni v6 split-message relay): compile, then build traced image c228rtt from the c228 tree.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
.venv/bin/python -m py_compile c228/app/packet.py c228/app/records.py && echo compiled
(cd c228 && ../.venv/bin/python -c "import app.records, app.packet; print('imports ok')")
rm -rf /tmp/c228rtt /tmp/replay_build/c228rtt; mkdir -p /tmp/c228rtt
cp -r c228/. /tmp/c228rtt/
python3 tools/add_trace_dan0l.py /tmp/c228rtt /tmp/replay_build/c228rtt > /dev/null && bash tools/build_harness.sh ditto-harness:c228rtt /tmp/replay_build/c228rtt | tail -1
