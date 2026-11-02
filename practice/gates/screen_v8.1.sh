#!/bin/bash
# v8.1 (harness/v8.1 HEAD): pack what ships, ditto verify, static screen against the released dan0l v30
# source and against the uploaded v6 package, every horizon version's public history for the lineage,
# the lineage packet (parent v6) and an L1 dry run. No model calls.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
echo "===== pack v8.1 at $(git -c safe.directory='*' rev-parse --short HEAD)"
bash tools/pack_submission.sh v8 practice/submission_v8.1.tgz | tail -2
rm -rf /tmp/packed_v81 /tmp/packed_v6 && mkdir -p /tmp/packed_v81 /tmp/packed_v6
tar -xzf practice/submission_v8.1.tgz -C /tmp/packed_v81
tar -xzf practice/submission_v6.tgz -C /tmp/packed_v6
echo "shipped files: $(find /tmp/packed_v81 -type f | wc -l)"; find /tmp/packed_v81 -maxdepth 1 -type f -printf '  %f\n'
grep -rlE "trace|HARNESS_TRACE" /tmp/packed_v81/app | head -3 | sed 's/^/  trace mention: /'
echo "===== ditto verify"
(cd repos/ditto-subnet && env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy -u ALL_PROXY -u all_proxy proxychains4 -q /root/.local/bin/uv run --offline ditto verify --path /home/bittensor/ditto/practice/submission_v8.1.tgz 2>&1 | grep -E "^(sha256|size|result)|PASS|FAIL" | head -12)
echo "===== diff against the uploaded v6"
diff -rq /tmp/packed_v6 /tmp/packed_v81 | sed 's/^/  /'
echo "  changed lines: $(diff -r /tmp/packed_v6 /tmp/packed_v81 | grep -cE '^[<>]')"
echo "===== static screen against released dan0l v30"
python3 tools/screen_local.py /tmp/packed_v81 --ref released/dan0l-v30_95534e25/src --out practice/screen_v8.1pack_vs_v30.json | grep -E '^##|malicious|fingerprints:|review_leads:|n-gram|\[new\]'
echo "===== static screen against the uploaded v6"
python3 tools/screen_local.py /tmp/packed_v81 --ref /tmp/packed_v6 --out practice/screen_v8.1pack_vs_v6.json | grep -E '^##|malicious|fingerprints:|review_leads:|n-gram|\[new\]'
echo "===== public history of horizon v1-v6"
H=live/$(date -u +%F)/lineage; mkdir -p $H
V2=$(python3 -c "import json; print(json.load(open('live/2026-10-28/horizon_v2_pipeline.json'))['agent_id'])")
for pair in 1:d5f819e9-aeda-4c49-aad9-882c26417ad2 2:$V2 3:34817ef4-1032-482c-9e17-0f8db2839be2 4:67c01765-94a6-45d4-80a0-2a5e2517ccdf 5:c8b23c9f-b3cf-4a19-abb0-154050a6c8ae 6:b55c19f0-329d-459f-8de3-a887b8286606; do
  n=${pair%%:*}; id=${pair#*:}
  for e in pipeline summary; do
    out=$H/v$n.json; [ $e = summary ] && out=$H/v${n}_summary.json
    for i in 1 2 3; do timeout 60 curl -sf "https://platform-api.heyditto.ai/api/v1/public/agent/$id/$e" -o $out && break; sleep 5; done
  done
  python3 -c "import json; s=json.load(open('$H/v${n}_summary.json')); p=json.load(open('$H/v$n.json')); print(s['name'], 'v%s' % s['version'], s['status'], s['submitted_at'][:16], '| attempts', [(a['status'], a.get('quarantine_resolution')) for a in p.get('screening_attempts') or []])"
done
echo "===== lineage packet (parent v6)"
PY=.cache/screener-venv/bin/python
$PY tools/lineage_packet_local.py practice/submission_v8.1.tgz practice/lineage_v8.1.json --history $H \
  --version 1=practice/submission.tgz --version 2=practice/submission_v2.tgz --version 3=practice/submission_v3.tgz \
  --version 4=practice/submission_v4.tgz --version 5=practice/submission_v5.tgz --version 6=practice/submission_v6.tgz | head -16
echo "===== L1 dry run"
$PY tools/l1_review_local.py practice/submission_v8.1.tgz /tmp/l1_v81_dry.json --lineage practice/lineage_v8.1.json --dry-run | tail -3
