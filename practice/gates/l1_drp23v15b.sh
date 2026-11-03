#!/bin/bash
# Local L1 (paid, production reviewer settings) of drp23v15b with the classic lineage packet: parent = horizon v8
# (drp23v15, agent 31ad3a16, passed policy 13), history v1-v8. DRY=1 builds the packet and stops before any model call.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PKG=practice/submission_drp23v15b.tgz
PY=$PWD/.cache/screener-venv/bin/python
H=live/2026-11-03/lineage
mkdir -p $H
cp -n live/2026-11-02/lineage/v[1-7]*.json $H/
API=https://platform-api.heyditto.ai/api/v1/public/agent/31ad3a16-e7d6-47c2-bfd0-801bd7766fd7
timeout 60 curl -s "$API/pipeline" -o $H/v8.json
timeout 60 curl -s "$API/summary" -o $H/v8_summary.json
python3 -c "import json; d=json.load(open('$H/v8.json')); print('v8', d['status'], [(a['policy_version'], a['status']) for a in d['screening_attempts']])"
echo "package sha256: $(sha256sum $PKG | cut -c1-16)"
$PY tools/lineage_packet_local.py $PKG practice/lineage_drp23v15b_v8.json --history $H \
  --version 1=practice/submission.tgz --version 2=practice/submission_v2.tgz --version 3=practice/submission_v3.tgz \
  --version 4=practice/submission_v4.tgz --version 5=practice/submission_v5.tgz --version 6=practice/submission_v6.tgz \
  --version 7=practice/submission_v8.1.tgz --version 8=practice/submission_drp23v15.tgz | head -8
if [ -n "$DRY" ]; then
  $PY tools/l1_review_local.py $PKG /tmp/l1_drp23v15b_dry.json --lineage practice/lineage_drp23v15b_v8.json --dry-run | tail -3
  exit 0
fi
.venv/bin/python tools/key_usage.py
$PY tools/l1_review_local.py $PKG practice/l1_drp23v15b_v8.json --lineage practice/lineage_drp23v15b_v8.json > practice/gates/l1_drp23v15b.log 2>&1
echo "L1 exit $?"; tail -40 practice/gates/l1_drp23v15b.log | grep -v 'review step'
.venv/bin/python tools/key_usage.py
