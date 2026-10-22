#!/bin/bash
# Local build of harness/ with apt stall timeouts. The real Dockerfile is not changed: a temporary
# copy gets one extra apt-config line after every FROM, so a stalled package download is dropped
# after 15 s and retried. The whole build is retried up to 3 times.
#
#   bash tools/build_harness.sh [tag]        (default tag: ditto-harness:dev)
set -uo pipefail
[ -f /etc/profile.d/zz-proxy.sh ] && source /etc/profile.d/zz-proxy.sh
HERE=$(cd "$(dirname "$0")/.." && pwd)
TAG=${1:-ditto-harness:dev}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
APT_LINE='RUN echo '"'"'Acquire::http::Timeout "15"; Acquire::https::Timeout "15"; Acquire::Retries "20";'"'"' > /etc/apt/apt.conf.d/96net-timeouts'
awk -v line="$APT_LINE" '{print} /^FROM /{print line}' "$HERE/harness/Dockerfile" > "$TMP/Dockerfile.local"
for attempt in 1 2 3; do
  echo "=== build attempt $attempt ($TAG)"
  if docker build --progress=plain -f "$TMP/Dockerfile.local" -t "$TAG" "$HERE/harness" > "$TMP/build.log" 2>&1; then
    grep -E "smoke|passed|naming to" "$TMP/build.log" | tail -12
    echo "=== built $TAG"
    exit 0
  fi
  echo "--- attempt $attempt failed, last lines:"; tail -15 "$TMP/build.log"
  sleep 5
done
exit 1
