#!/bin/bash
# Pack a harness tree into a submission tarball: Dockerfile at the root, no caches, no secrets,
# no trace hooks (the tree is packed as it is in git; practice builds add tracing elsewhere).
#
#   bash tools/pack_submission.sh [TREE] [OUT]      (default: combined -> practice/submission.tgz)
#   SHIP_DECLARATION=1 bash tools/pack_submission.sh drp22v15 OUT    (a released king's DECLARATION.md goes too)
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
# DECLARATION.md stays in the repository and is not shipped: it is optional, and horizon v1 cleared
# screening without one.
cp "$TREE/Dockerfile" "$TREE/requirements.txt" "$TREE/PROVENANCE.md" "$STAGE/"
# A tree built on a released king that shipped its own declaration keeps shipping it, with our rows added.
if [ -n "${SHIP_DECLARATION:-}" ]; then
  cp "$TREE/DECLARATION.md" "$STAGE/"
fi
# A base's license (Hades ships MIT) goes with its code.
if [ -f "$TREE/LICENSE" ]; then
  cp "$TREE/LICENSE" "$STAGE/"
fi
cp -r "$TREE/app" "$STAGE/app"
find "$STAGE" -name __pycache__ -type d -prune -exec rm -rf {} +
# FORMAT=1: ship app/ in our own house style (ruff format, 79 columns, single quotes). The tree in git keeps
# the base's layout so practice trace hooks still apply; the packed code must parse to the same AST.
if [ -n "${FORMAT:-}" ]; then
  /home/bittensor/ditto/repos/ditto-subnet/.venv/bin/ruff format --quiet --line-length 79 \
    --config "format.quote-style='single'" "$STAGE/app"
  python3 - "$TREE/app" "$STAGE/app" <<'PY'
import ast, pathlib, sys
a, b = map(pathlib.Path, sys.argv[1:3])
bad = [str(f.relative_to(a)) for f in sorted(a.rglob("*.py"))
       if ast.dump(ast.parse(f.read_text())) != ast.dump(ast.parse((b / f.relative_to(a)).read_text()))]
if bad:
    sys.exit(f"formatting changed the AST of {bad}; not packing")
print("formatted app/: AST identical to the tree")
PY
fi
if grep -rIl -E 'sk-or-v1-|sk-[A-Za-z0-9]{32,}|BEGIN (RSA|OPENSSH|EC) PRIVATE' "$STAGE"; then
  echo "secret-looking content found, not packing" >&2
  exit 1
fi
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-01-01' -C "$STAGE" -czf "$OUT" .
echo "packed $OUT from $TREE at $(git rev-parse --short HEAD): $(tar -tzf "$OUT" | grep -vc '/$') files, $(du -h "$OUT" | cut -f1)"
sha256sum "$OUT"
