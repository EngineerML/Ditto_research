#!/bin/bash
# drp23v15 (DrPresident v23 + unlinked tools left out), free screening steps: pack what would ship (with the
# king's DECLARATION.md), ditto verify, static screen against the released DrPresident v23, the lineage packet
# both ways (parent: our horizon v7; released base: DrPresident v23) and an L1 dry run on each. No model calls.
# The probe battery runs separately: bash practice/gates/probe_drp22v15.sh drp23v15=... drp23ref=...
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PKG=practice/submission_drp23v15.tgz
PY=$PWD/.cache/screener-venv/bin/python
BASE=released/DrPresident-v23_8474358a
echo "===== 1. pack drp23v15 at $(git rev-parse --short HEAD)"
SHIP_DECLARATION=1 bash tools/pack_submission.sh drp23v15 $PKG | tail -2 || exit 1
rm -rf /tmp/packed_d23 && mkdir -p /tmp/packed_d23 && tar -xzf $PKG -C /tmp/packed_d23
echo "shipped: $(find /tmp/packed_d23 -type f | wc -l) files"; find /tmp/packed_d23 -maxdepth 1 -type f -printf '  %f\n'
grep -rlE "HARNESS_TRACE|add_trace" /tmp/packed_d23/app | sed 's/^/  trace mention: /'
echo "===== 2. ditto verify"
(cd repos/ditto-subnet && env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy proxychains4 -q /root/.local/bin/uv run --offline ditto verify --path /home/bittensor/ditto/$PKG 2>&1 | grep -E "^(sha256|size|result)|PASS|FAIL" | head -12)
echo "===== 3. static screen against released DrPresident v23"
diff -rq $BASE/src /tmp/packed_d23 | sed 's/^/  /'
echo "  changed lines: $(diff -r $BASE/src /tmp/packed_d23 | grep -cE '^[<>]')"
python3 tools/screen_local.py /tmp/packed_d23 --ref $BASE/src --out practice/screen_drp23v15_vs_drp23.json | grep -E '^##|malicious|fingerprints:|review_leads:|n-gram|\[new\]'
echo "===== 4a. lineage packet, classic parent (our horizon v7)"
H=live/2026-11-02/lineage
$PY tools/lineage_packet_local.py $PKG practice/lineage_drp23v15_v7.json --history $H \
  --version 1=practice/submission.tgz --version 2=practice/submission_v2.tgz --version 3=practice/submission_v3.tgz \
  --version 4=practice/submission_v4.tgz --version 5=practice/submission_v5.tgz --version 6=practice/submission_v6.tgz \
  --version 7=practice/submission_v8.1.tgz | head -6
echo "===== 4b. lineage packet, released base (DrPresident v23, with v22 and v20 as its history)"
$PY tools/lineage_packet_local.py $PKG practice/lineage_drp23v15_base.json --history live/2026-11-02/lineage_drp \
  --reference-kind released_base --version 23=$BASE/agent.tar.gz \
  --version 22=released/DrPresident-v22_eeb26552/agent.tar.gz --version 20=released/DrPresident-v20_541b701a/agent.tar.gz | head -16
echo "===== 5. L1 dry runs"
for k in v7 base; do
  echo "--- $k"; $PY tools/l1_review_local.py $PKG /tmp/l1_drp23v15_${k}_dry.json --lineage practice/lineage_drp23v15_$k.json --dry-run | tail -3
done
echo "===== free steps done"
