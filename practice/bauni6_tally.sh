#!/bin/bash
# Grader-normalised tally of the 2026-11-16 bauni v6 runs: baseline (nt2 = 37bd158, d59 = dan0l v59), referring turns v1, v2 (phraseMeans).
cd /home/bittensor/ditto/practice/generator || exit 1
for r in 20261116T085747Z 20261116T091443Z 20261116T092706Z 20261116T094046Z; do
  echo "== $r"
  python3 ../list_tally.py $r nt2 d59 rt
done
