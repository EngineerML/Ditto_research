#!/bin/bash
# Local L1 source review (paid, production reviewer settings) of the drp22v15 tarball with its lineage packet
# (parent: horizon v7). Log: practice/gates/l1_drp22v15.log; observation: practice/l1_drp22v15.json.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
.venv/bin/python tools/key_usage.py
.cache/screener-venv/bin/python tools/l1_review_local.py practice/submission_drp22v15.tgz practice/l1_drp22v15.json \
  --lineage practice/lineage_drp22v15.json > practice/gates/l1_drp22v15.log 2>&1
echo "L1 exit $?"; tail -40 practice/gates/l1_drp22v15.log | grep -v 'review step'
.venv/bin/python tools/key_usage.py
