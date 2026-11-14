#!/bin/bash
# Pack lab/c228-v18 for upload (plain and ruff-formatted) and run every local copy check on each package.
#
#   bash practice/c228_dupcheck.sh
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
set -o pipefail
SHIP_DECLARATION=1 bash tools/pack_submission.sh c228 practice/submission_c228_plain.tgz | tail -2
SHIP_DECLARATION=1 FORMAT=1 FORMAT_LINE=88 FORMAT_QUOTE=double bash tools/pack_submission.sh c228 practice/submission_c228_fmt88.tgz | tail -2
for p in practice/submission_c228_plain.tgz practice/submission_c228_fmt88.tgz; do
  echo
  echo "################ $p  sha256 $(sha256sum "$p" | cut -c1-16)  files $(tar -tzf "$p" | grep -c -v '/$')"
  echo "== top fingerprint matches against released agents (window / line / containment) =="
  T=$(mktemp -d); tar -xzf "$p" -C "$T"
  for r in released/*/src; do
    .venv/bin/python tools/anticopy_check.py "$r" "$T" 2>/dev/null | tail -1 | sed "s#^$T#$(basename "$(dirname "$r")")#"
  done | sort -t' ' -k4 -r | head -6
  rm -rf "$T"
  echo "== unreleased-copy pair score vs other-owner unreleased agents we hold (horizon v10), threshold 100 =="
  .venv/bin/python tools/unreleased_copy_check.py "$p" practice/submission_d42c.tgz 2>&1 | tail -4
done
echo
echo "== same sha as any earlier package we built? =="
sha256sum practice/submission_*.tgz | sort | awk '{print $1}' | uniq -d | head
