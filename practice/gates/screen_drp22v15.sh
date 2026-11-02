#!/bin/bash
# drp22v15 (DrPresident v22 + unlinked tools left out), free screening steps: pack what would ship (with the
# king's DECLARATION.md), ditto verify, static screen against the released DrPresident v22, the screener's
# zero-token probe battery on an image built from the tarball, the lineage packet (parent: our horizon v7)
# and an L1 dry run. No model calls.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PKG=practice/submission_drp22v15.tgz
PY=$PWD/.cache/screener-venv/bin/python
echo "===== 1. pack drp22v15 at $(git rev-parse --short HEAD)"
SHIP_DECLARATION=1 bash tools/pack_submission.sh drp22v15 $PKG | tail -2 || exit 1
SHA=$(sha256sum $PKG | cut -d' ' -f1)
rm -rf /tmp/packed_d15 && mkdir -p /tmp/packed_d15 && tar -xzf $PKG -C /tmp/packed_d15
echo "shipped: $(find /tmp/packed_d15 -type f | wc -l) files"; find /tmp/packed_d15 -maxdepth 1 -type f -printf '  %f\n'
grep -rlE "HARNESS_TRACE|add_trace" /tmp/packed_d15/app | sed 's/^/  trace mention: /'
echo "===== 2. ditto verify"
(cd repos/ditto-subnet && env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy proxychains4 -q /root/.local/bin/uv run --offline ditto verify --path /home/bittensor/ditto/$PKG 2>&1 | grep -E "^(sha256|size|result)|PASS|FAIL" | head -12)
echo "===== 3. static screen against released DrPresident v22"
diff -rq released/DrPresident-v22_eeb26552/src /tmp/packed_d15 | sed 's/^/  /'
echo "  changed lines: $(diff -r released/DrPresident-v22_eeb26552/src /tmp/packed_d15 | grep -cE '^[<>]')"
python3 tools/screen_local.py /tmp/packed_d15 --ref released/DrPresident-v22_eeb26552/src --out practice/screen_drp22v15_vs_drp22.json | grep -E '^##|malicious|fingerprints:|review_leads:|n-gram|\[new\]'
echo "===== 4. probe battery (zero-token, bench 15)"
S=/tmp/probe_drp22v15; rm -rf $S
(cd repos/ditto-subnet/workers/screener && timeout 900 $PY -m ditto_screener.probe_review prepare --archive /home/bittensor/ditto/$PKG --sha256 $SHA --out $S --bench-version 15 --allow-host-daemon > practice/probe_drp22v15_prepare.json 2>&1; echo "  prepare exit $?"; tail -c 600 practice/probe_drp22v15_prepare.json 2>/dev/null)
(cd repos/ditto-subnet/workers/screener && timeout 900 $PY -m ditto_screener.probe_review battery --session $S > /home/bittensor/ditto/practice/probe_drp22v15_battery.json 2>&1; echo "  battery exit $?")
(cd repos/ditto-subnet/workers/screener && $PY -m ditto_screener.probe_review stop --session $S > /dev/null 2>&1)
echo "===== 5. lineage packet (parent v7) and L1 dry run"
H=live/2026-11-02/lineage
for e in pipeline summary; do
  out=$H/v7.json; [ $e = summary ] && out=$H/v7_summary.json
  timeout 60 curl -sf "https://platform-api.heyditto.ai/api/v1/public/agent/92b9aec4-3642-4b0d-872f-9ce516cb7b7e/$e" -o $out
done
$PY tools/lineage_packet_local.py $PKG practice/lineage_drp22v15.json --history $H \
  --version 1=practice/submission.tgz --version 2=practice/submission_v2.tgz --version 3=practice/submission_v3.tgz \
  --version 4=practice/submission_v4.tgz --version 5=practice/submission_v5.tgz --version 6=practice/submission_v6.tgz \
  --version 7=practice/submission_v8.1.tgz | head -16
$PY tools/l1_review_local.py $PKG /tmp/l1_drp22v15_dry.json --lineage practice/lineage_drp22v15.json --dry-run | tail -3
echo "===== free steps done"
