#!/bin/bash
# Free: reach of the asked-name filter in tied_names_view on v18 datagen seeds and every local generator pack.
cd /home/bittensor/ditto || exit 1
.venv/bin/python practice/c228_askedrun_static.py .cache/v18sets/*.json $(ls .cache/miner_gens/packs/*/*.json | grep -v -E '/(fix1|fq-v2-p1|sr4-p1)/') 2>&1 | grep -v "ties dropped in 0$"
