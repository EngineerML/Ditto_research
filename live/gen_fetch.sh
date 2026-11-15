#!/bin/bash
# Download a released generator source archive into its own empty folder and extract it (data only, nothing run).
#   bash live/gen_fetch.sh SUBMISSION_ID FOLDER_NAME
source /etc/profile.d/zz-proxy.sh
sid=$1; name=$2
out=/home/bittensor/ditto/.cache/miner_gens/dl/$name
[ -e "$out" ] && { echo "exists: $out"; exit 1; }
mkdir -p "$out/src"
B=https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/$sid
curl -s --max-time 30 "$B" -o "$out/meta.json"
curl -s --max-time 120 -L "$B/archive" -o "$out/archive.bin"
ls -l "$out/archive.bin"; file "$out/archive.bin"
sha256sum "$out/archive.bin"; grep -o '"source_sha256":"[0-9a-f]*"' "$out/meta.json"
tar -xf "$out/archive.bin" -C "$out/src" --no-same-owner --no-same-permissions 2>&1 | head -3
find "$out/src" -type f | head -60
du -sh "$out/src"
