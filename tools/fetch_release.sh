#!/bin/bash
# Download a released SN118 king artifact, verify its SHA-256, and unpack it safely (nothing is executed).
set -euo pipefail
source /etc/profile.d/zz-proxy.sh
API=https://platform-api.heyditto.ai
AGENT=${1:?agent id}
LABEL=${2:?label}
DEST=/home/bittensor/ditto/released/$LABEL
mkdir -p "$DEST"
cd "$DEST"
meta=$(curl -sS -f --max-time 40 "$API/api/v1/public/agent/$AGENT/artifact")   # signed URL lives 5 minutes
echo "$meta" | python3 -c "import json,sys; d=json.load(sys.stdin); d.pop('download_url',None); print(json.dumps(d, indent=1))" > release.json
url=$(echo "$meta" | python3 -c "import json,sys; print(json.load(sys.stdin)['download_url'])")
want=$(echo "$meta" | python3 -c "import json,sys; print(json.load(sys.stdin)['sha256'])")
curl -sS -f --max-time 300 "$url" -o agent.tar.gz
got=$(sha256sum agent.tar.gz | cut -d' ' -f1)
echo "size: $(stat -c %s agent.tar.gz) bytes"
[ "$got" = "$want" ] && echo "sha256 OK: $got" || { echo "SHA256 MISMATCH: got $got want $want"; exit 1; }
# refuse absolute paths, parent-dir escapes, and links before extracting
python3 - <<'PY'
import tarfile
bad = []
with tarfile.open("agent.tar.gz") as t:
    for m in t.getmembers():
        if m.name.startswith("/") or ".." in m.name.split("/") or m.issym() or m.islnk() or m.isdev():
            bad.append(m.name)
print("unsafe members:", bad or "none")
raise SystemExit(1 if bad else 0)
PY
mkdir -p src
tar -xzf agent.tar.gz -C src --no-same-owner --no-same-permissions
echo "--- unpacked files:"
find src -type f | sed 's#^src/##' | sort | head -80
echo "total files: $(find src -type f | wc -l)"
