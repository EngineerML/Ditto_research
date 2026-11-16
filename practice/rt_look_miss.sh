#!/bin/bash
# One remaining half-score of the phraseMeans run: the records around the asked name, the calls, and the reply.
cd /home/bittensor/ditto || exit 1
python3 practice/rt_look.py practice/generator/20261116T092706Z pack-1-r0 rt ${1:-coref-mix-t1-000} 2>&1 | grep -E '^Q:|^events|phraseMeans"|Gisela|^FINAL|call [0-9]|output' | cut -c1-400 | head -40
