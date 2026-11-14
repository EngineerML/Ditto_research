#!/bin/bash
# Upload package overhorizoner v5 (lab/c228-v18): formatted pack, copy checks, build and smoke-test the exact tarball.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
OUT=practice/submission_c228_v5.tgz
SHIP_DECLARATION=1 FORMAT=1 FORMAT_LINE=88 FORMAT_QUOTE=double bash tools/pack_submission.sh c228 "$OUT" | tail -2
echo "== stray files"; tar -tzf "$OUT" | grep -iE "\.env|secret|pycache|\.pyc|trace" || echo "none"
echo "== copy checks vs released agents"
T=$(mktemp -d); tar -xzf "$OUT" -C "$T"
for r in released/*/src; do
  .venv/bin/python tools/anticopy_check.py "$r" "$T" 2>/dev/null | tail -1 | sed "s#^$T#$(basename "$(dirname "$r")")#"
done | sort -t' ' -k4 -r | head -4
echo "== unreleased-copy vs horizon v10 (other owner)"
.venv/bin/python tools/unreleased_copy_check.py "$OUT" practice/submission_d42c.tgz 2>&1 | tail -1
rm -rf "$T"
echo "== same sha as an earlier package?"
sha256sum practice/submission_*.tgz | awk '{print $1}' | sort | uniq -d
bash practice/c228_pkg_smoke.sh "$OUT" 2>&1 | tail -5
docker run -d --rm --name c228v5health -p 18999:8080 -e OPENROUTER_API_KEY=mock ditto-harness:c228pkg > /dev/null
for i in $(seq 1 30); do out=$(curl -s --max-time 2 http://127.0.0.1:18999/health) && [ -n "$out" ] && break; sleep 1; done
echo "health: $out"; docker stop c228v5health > /dev/null
sha256sum "$OUT"
