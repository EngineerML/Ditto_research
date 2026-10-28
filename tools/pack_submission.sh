#!/bin/bash
# Pack a harness tree into a submission tarball: Dockerfile at the root, no caches, no secrets,
# no trace hooks (the tree is packed as it is in git; practice builds add tracing elsewhere).
#
#   bash tools/pack_submission.sh [TREE] [OUT]      (default: combined -> practice/submission.tgz)
set -euo pipefail
cd /home/bittensor/ditto
TREE=${1:-combined}
OUT=${2:-practice/submission.tgz}
if [ -n "$(git status --porcelain -- "$TREE")" ]; then
  echo "$TREE has uncommitted changes; commit first so the tarball matches a commit" >&2
  exit 1
fi
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp "$TREE/Dockerfile" "$TREE/requirements.txt" "$TREE/PROVENANCE.md" "$TREE/DECLARATION.md" "$STAGE/"
cp -r "$TREE/app" "$STAGE/app"
find "$STAGE" -name __pycache__ -type d -prune -exec rm -rf {} +
if grep -rIl -E 'sk-or-v1-|sk-[A-Za-z0-9]{32,}|BEGIN (RSA|OPENSSH|EC) PRIVATE' "$STAGE"; then
  echo "secret-looking content found, not packing" >&2
  exit 1
fi
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-01-01' -C "$STAGE" -czf "$OUT" .
echo "packed $OUT from $TREE at $(git rev-parse --short HEAD): $(tar -tzf "$OUT" | grep -vc '/$') files, $(du -h "$OUT" | cut -f1)"
sha256sum "$OUT"
