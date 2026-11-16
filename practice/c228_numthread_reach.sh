#!/bin/bash
# Free: reach of the number_threads port on v18 datagen seeds and every local generator pack.
cd /home/bittensor/ditto || exit 1
.venv/bin/python practice/c228_numthread_reach.py .cache/v18sets/*.json $(ls .cache/miner_gens/packs/*/*.json | grep -v -E '/(fix1|fq-v2-p1|sr4-p1)/') 2>&1 | tail -40
