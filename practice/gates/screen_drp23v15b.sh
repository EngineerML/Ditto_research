#!/bin/bash
# drp23v15b free screening steps: pack what would ship (with DECLARATION.md), ditto verify, static screen against the
# released DrPresident v23 and against v8 (drp23v15). No model calls.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PKG=practice/submission_drp23v15b.tgz
BASE=released/DrPresident-v23_8474358a
echo "===== 1. pack drp23v15b at $(git rev-parse --short HEAD)"
SHIP_DECLARATION=1 bash tools/pack_submission.sh drp23v15b $PKG | tail -2 || exit 1
rm -rf /tmp/packed_d23b && mkdir -p /tmp/packed_d23b && tar -xzf $PKG -C /tmp/packed_d23b
echo "shipped: $(find /tmp/packed_d23b -type f | wc -l) files"
grep -rlE "HARNESS_TRACE|add_trace" /tmp/packed_d23b/app | sed 's/^/  trace mention: /'
echo "===== 2. ditto verify"
(cd repos/ditto-subnet && env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy proxychains4 -q /root/.local/bin/uv run --offline ditto verify --path /home/bittensor/ditto/$PKG 2>&1 | grep -E "^(sha256|size|result)|PASS|FAIL" | head -12)
echo "===== 3. static screen against released DrPresident v23"
diff -rq $BASE/src /tmp/packed_d23b | sed 's/^/  /'
python3 tools/screen_local.py /tmp/packed_d23b --ref $BASE/src --out practice/screen_drp23v15b_vs_drp23.json | grep -E '^##|malicious|fingerprints:|review_leads:|n-gram|\[new\]|\[inherited\]'
echo "===== 4. static screen against v8 (drp23v15)"
rm -rf /tmp/packed_d23 && mkdir -p /tmp/packed_d23 && tar -xzf practice/submission_drp23v15.tgz -C /tmp/packed_d23
diff -r /tmp/packed_d23 /tmp/packed_d23b | grep -cE '^[<>]' | sed 's/^/  changed lines vs v8: /'
python3 tools/screen_local.py /tmp/packed_d23b --ref /tmp/packed_d23 --out practice/screen_drp23v15b_vs_v8.json | grep -E 'malicious|fingerprints:|review_leads:|\[new\]'
echo "===== free steps done"
