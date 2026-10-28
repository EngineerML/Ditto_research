#!/bin/bash
# Build the screener's L2 analyzer image (workers/screener/deploy/l2-analyzer.Dockerfile) as
# ditto-screener-l2-analyzer:local. The Dockerfile is not changed: a temporary copy gets the apt stall
# timeouts after FROM, as tools/build_harness.sh does for harness images.
set -uo pipefail
[ -f /etc/profile.d/zz-proxy.sh ] && source /etc/profile.d/zz-proxy.sh
HERE=$(cd "$(dirname "$0")/.." && pwd)
CTX=$HERE/repos/ditto-subnet/workers/screener
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
APT_LINE='RUN echo '"'"'Acquire::http::Timeout "15"; Acquire::https::Timeout "15"; Acquire::Retries "20";'"'"' > /etc/apt/apt.conf.d/96net-timeouts'
awk -v apt="$APT_LINE" '{print} /^FROM /{print apt}' "$CTX/deploy/l2-analyzer.Dockerfile" > "$TMP/Dockerfile.local"
for attempt in 1 2 3; do
  echo "=== build attempt $attempt"
  if docker build --progress=plain -f "$TMP/Dockerfile.local" -t ditto-screener-l2-analyzer:local "$CTX" > "$TMP/build.log" 2>&1; then
    tail -3 "$TMP/build.log"
    echo "=== built ditto-screener-l2-analyzer:local"
    exit 0
  fi
  echo "--- attempt $attempt failed:"; tail -12 "$TMP/build.log"
  sleep 5
done
exit 1
