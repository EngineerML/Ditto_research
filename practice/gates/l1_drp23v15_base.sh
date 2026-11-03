#!/bin/bash
# Local L1 source review (paid, production reviewer settings) of the drp23v15 tarball with its released-base lineage
# packet (reference: DrPresident v23, diff scope). Log: practice/gates/l1_drp23v15_base.log;
# observation: practice/l1_drp23v15_base.json.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
.venv/bin/python tools/key_usage.py
.cache/screener-venv/bin/python tools/l1_review_local.py practice/submission_drp23v15.tgz practice/l1_drp23v15_base.json \
  --lineage practice/lineage_drp23v15_base.json > practice/gates/l1_drp23v15_base.log 2>&1
echo "L1 exit $?"; tail -40 practice/gates/l1_drp23v15_base.log | grep -v 'review step'
.venv/bin/python tools/key_usage.py
