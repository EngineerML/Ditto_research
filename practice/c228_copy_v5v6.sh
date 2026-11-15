#!/bin/bash
# Copy scores of the v5 (passed screening) and v6 packages against released crown-v228.
cd /home/bittensor/ditto || exit 1
for v in v5 v6; do
  T=$(mktemp -d); tar -xzf practice/submission_c228_$v.tgz -C "$T"
  echo "$v: $(.venv/bin/python tools/anticopy_check.py released/crown-v228-v1_673386d0/src "$T" 2>/dev/null | tail -1 | sed "s#^$T##")"
  rm -rf "$T"
done
grep -rn -i "excuse\|release.*exempt\|released agent" notes/2026-11-14_c228_rebase.md | head -5
