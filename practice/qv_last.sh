#!/bin/bash
# Misses of the latest paid generator run for agent a on its pack-1.
cd /home/bittensor/ditto || exit 1
d=$(ls -td practice/generator/2026*Z | head -1); echo $d
python3 practice/qv2_misses.py $d ${1:-pack-1-r0} a 2>&1 | head -${2:-100}
