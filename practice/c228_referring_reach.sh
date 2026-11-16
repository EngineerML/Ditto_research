#!/bin/bash
# Free: reach of referring_turns on the bauni v6 packs, v18 datagen seeds and every other local generator pack.
cd /home/bittensor/ditto || exit 1
grep -n "session_id" c228/app/protocol.py | head -3
.venv/bin/python practice/c228_referring_reach.py .cache/miner_gens/packs/bauni6/*.json .cache/v18sets/*.json $(ls .cache/miner_gens/packs/*/*.json | grep -v -E '/(fix1|fq-v2-p1|sr4-p1|bauni6|bauni6-p1)/') 2>&1 | grep -v -E "reached +0 evidence" | head -60
