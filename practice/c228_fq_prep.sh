#!/bin/bash
# Build 5FqQq9 v2 (pollen-probe 0.9, f5659f80) slice packs in the sandbox, as a v18 dueling column asks for them.
cd /home/bittensor/ditto || exit 1
GRADING_BENCH=18 GRADING_BENCHES= MINER_HOTKEY=5FqQq9WLy3RXrnSMhR48ennfCESRG46oPLJT4LpGXp6VJjAg \
  bash tools/gen_pack_sandbox.sh .cache/miner_gens/dl/5FqQq9WL_f5659f80/src .cache/miner_gens/packs/fq-v2 35 1 2 2>&1 | tail -5
python3 - <<'P'
import json, collections
p = json.load(open("/home/bittensor/ditto/.cache/miner_gens/packs/fq-v2/pack-1.json"))
print(collections.Counter(c["id"].rsplit("-", 1)[0] for c in p["cases"]))
c = p["cases"][0]
print(c["question"], "| gold:", c["expected_answer"], "| distractors:", c.get("distractor_answers"))
P
echo "== images"
docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedSince}}' | grep -E "ditto-harness:(c228|crown)" | head -20
