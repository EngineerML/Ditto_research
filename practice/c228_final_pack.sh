#!/bin/bash
# Final upload package for overhorizoner (lab/c228-v18): formatted pack, copy checks, then build that exact tarball
# and answer a free mock pack run with it.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
git add c228/DECLARATION.md practice/c228_dupcheck.sh practice/c228_final_pack.sh
git commit -qm "c228: declaration names the released base by uuid and sha; pack and copy-check scripts" && git log --oneline -1
OUT=practice/submission_c228_v1.tgz
SHIP_DECLARATION=1 FORMAT=1 FORMAT_LINE=88 FORMAT_QUOTE=double bash tools/pack_submission.sh c228 "$OUT" | tail -2
echo "== contents"; tar -tzf "$OUT" | grep -v '/$' | head -50 | tr '\n' ' '; echo
echo "== secrets / stray files"; tar -tzf "$OUT" | grep -iE "\.env|key|secret|pycache|\.pyc|trace" || echo "none"
echo "== copy checks"
T=$(mktemp -d); tar -xzf "$OUT" -C "$T"
for r in released/*/src; do
  .venv/bin/python tools/anticopy_check.py "$r" "$T" 2>/dev/null | tail -1 | sed "s#^$T#$(basename "$(dirname "$r")")#"
done | sort -t' ' -k4 -r | head -4
.venv/bin/python tools/unreleased_copy_check.py "$OUT" practice/submission_d42c.tgz 2>&1 | tail -1
echo "== build that tarball and smoke-test it (mock, free)"
B=$(mktemp -d); tar -xzf "$OUT" -C "$B"
python3 tools/add_trace_dan0l.py "$B" /tmp/replay_build/c228pkt > /dev/null && bash tools/build_harness.sh ditto-harness:c228pkt /tmp/replay_build/c228pkt 2>&1 | tail -1
timeout 900 .venv/bin/python tools/generator_panel.py --mock --packs .cache/miner_gens/packs/s26111-seed1 --agent pkg=c228pkt --concurrency 6 > /tmp/c228_pkg_mock.log 2>&1
d=$(ls -td practice/generator/*-mock | head -1)
for f in "$d"/trace/*/pkg/trace.jsonl; do echo "  $(basename "$(dirname "$(dirname "$f")")") answered $(wc -l < "$f")"; done
grep -ci traceback /tmp/c228_pkg_mock.log
rm -rf "$T" "$B"
sha256sum "$OUT"
