#!/bin/bash
# Free: which cases get the current-list note, over v18 datagen seeds and every local pack.
cd /home/bittensor/ditto || exit 1
.venv/bin/python practice/qv_note_reach.py .cache/v18sets/*.json $(ls .cache/miner_gens/packs/*/*.json | grep -v -E '/(fix1|fq-v2-p1|sr4-p1|bauni6-p1|qv2-p1)/') 2>&1 | tail -20
