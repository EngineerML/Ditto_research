#!/bin/bash
# Local build of harness/ with apt and pip stall timeouts. The real Dockerfile is not changed: a temporary
# copy gets an apt-config line and pip timeout settings after every FROM, so a stalled download is dropped
# after 15 s and retried. The whole build is retried up to 3 times.
#
#   bash tools/build_harness.sh [tag] [source dir]   (defaults: ditto-harness:dev, harness/)
set -uo pipefail
[ -f /etc/profile.d/zz-proxy.sh ] && source /etc/profile.d/zz-proxy.sh
HERE=$(cd "$(dirname "$0")/.." && pwd)
TAG=${1:-ditto-harness:dev}
SRC=${2:-$HERE/harness}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
APT_LINE='RUN echo '"'"'Acquire::http::Timeout "15"; Acquire::https::Timeout "15"; Acquire::Retries "20";'"'"' > /etc/apt/apt.conf.d/96net-timeouts'
PIP_LINE='ENV PIP_DEFAULT_TIMEOUT=15 PIP_RETRIES=10'
awk -v apt="$APT_LINE" -v pip="$PIP_LINE" '{print} /^FROM /{print apt; print pip}' "$SRC/Dockerfile" > "$TMP/Dockerfile.local"
for attempt in 1 2 3; do
  echo "=== build attempt $attempt ($TAG)"
  if docker build --progress=plain -f "$TMP/Dockerfile.local" -t "$TAG" "$SRC" > "$TMP/build.log" 2>&1; then
    grep -E "smoke|passed|naming to" "$TMP/build.log" | tail -12
    echo "=== built $TAG"
    exit 0
  fi
  echo "--- attempt $attempt failed, last lines:"; tail -15 "$TMP/build.log"
  sleep 5
done
exit 1
