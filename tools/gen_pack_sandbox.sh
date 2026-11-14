#!/bin/bash
# Build a released miner generator inside a throwaway Go container and write challenge packs from it.
#
#   bash tools/gen_pack_sandbox.sh SRC_DIR OUT_DIR [CASES] [SEED...]
#
# SRC_DIR is an extracted generator source (main.go, go.mod, vendor/). It is untrusted code, so it is only
# ever built and run inside the container: no network, read-only source, all capabilities dropped, no new
# privileges, the user nobody, and a size-capped tmpfs for the build cache. Each pack is a fresh request
# on stdin, as a live round sends it; OUT_DIR gets one pack-<n>.json per seed.
set -euo pipefail
SRC=$(realpath "$1")
OUT=$(realpath -m "$2")
CASES=${3:-35}
shift $(( $# < 3 ? $# : 3 ))
SEEDS=("$@")
if [ ${#SEEDS[@]} -eq 0 ]; then
  SEEDS=(1 2 3)
fi
# The Go 1.27.3 image the scorer sandbox uses (golang@sha256:972b4110...).
IMG=${GO_IMAGE:-golang@sha256:972b4110ba0f47539a975c31e52c64765e1ff19f2d74469ae4a595c6676e80a5}
mkdir -p "$OUT"
chmod 777 "$OUT"
# Request shape. Defaults are the old practice request (v13 baseline, accepts 13..16). A dueling slice column
# pins one policy and sends no list (challenge.SliceGenerateRequest), with the column's own generator hotkey:
#   GRADING_BENCH=17 GRADING_BENCHES= MINER_HOTKEY=5Hb5... bash tools/gen_pack_sandbox.sh ...
GBV=${GRADING_BENCH:-13}
GBV_LIST=${GRADING_BENCHES-13,14,15,16}
GBVS=""
if [ -n "$GBV_LIST" ]; then GBVS=",\"grading_bench_versions\":[$GBV_LIST]"; fi
HOTKEY=${MINER_HOTKEY:-5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY}
REQS=$(mktemp -d)
trap 'rm -rf "$REQS"' EXIT
n=0
for s in "${SEEDS[@]}"; do
  n=$((n + 1))
  hex=$(printf '%s' "practice-seed-$s" | sha256sum | cut -c1-64)
  printf '{"contract":"dittobench-generator/v1","seed":"%s","miner_hotkey":"%s","cases":%d,"grading_bench_version":%d%s}\n' \
    "$hex" "$HOTKEY" "$CASES" "$GBV" "$GBVS" > "$REQS/req-$n.json"
done
chmod -R a+rX "$REQS"
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 \
  --memory 2g --pids-limit 256 \
  --tmpfs /tmp:rw,size=1g,exec \
  -e HOME=/tmp -e GOCACHE=/tmp/gocache -e GOPATH=/tmp/gopath -e GOFLAGS=-mod=vendor -e GOTOOLCHAIN=local -e CGO_ENABLED=0 \
  -v "$SRC":/src:ro -v "$REQS":/reqs:ro -v "$OUT":/out \
  -w /src "$IMG" sh -c '
    go build -o /tmp/gen . || exit 1
    for r in /reqs/req-*.json; do
      k=$(basename "$r" .json | cut -d- -f2)
      timeout 120 /tmp/gen < "$r" > /out/pack-$k.json || { echo "pack $k failed" >&2; exit 1; }
    done'
for f in "$OUT"/pack-*.json; do
  python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(sys.argv[1].rsplit("/",1)[1], "cases", len(p["cases"]), "waves", len(p["memory_waves"]), "pairs", sum(len(w.get("pairs") or []) for w in p["memory_waves"]), "grading", p["grading_bench_version"], "generator", p["generator"])' "$f"
done
