"""Run the screener's deterministic source checks on a local harness tree (no model, no build).

    python3 tools/screen_local.py TREE [--ref REF_TREE] [--out OUT.json]

Uses the upstream screener's own scanners (repos/ditto-subnet/workers/screener), read-only:
- find_decisive_malicious_source: high-confidence pre-build quarantine findings;
- find_benchmark_emulation_fingerprints: C13 benchmark-emulation fingerprints (leads);
- find_source_review_leads: the static leads the L1 source review is pointed at;
- the v14 generator-template n-gram scan (scripts/report_generator_ngram_leads.py).
All of these are location-only leads, not verdicts: the screener's reviewers decide. With --ref
(a tree that already cleared screening, such as a released king), each lead is marked
"inherited" when the reference has the same kind in the same file, else "new".
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SCREENER = HERE / "repos" / "ditto-subnet" / "workers" / "screener"
sys.path.insert(0, str(SCREENER))
from ditto_screener.source_signals import (  # noqa: E402
    find_benchmark_emulation_fingerprints,
    find_decisive_malicious_source,
    find_source_review_leads,
)

_spec = importlib.util.spec_from_file_location("ngram_leads", SCREENER / "scripts" / "report_generator_ngram_leads.py")
ngram = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ngram)

SKIP_PARTS = {"__pycache__", ".git", ".venv", "node_modules"}


def read_tree(root: Path) -> list[tuple[str, str]]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or SKIP_PARTS & set(path.parts):
            continue
        try:
            files.append((path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue
    return files


def scan(root: Path) -> dict[str, object]:
    files = read_tree(root)
    return {
        "files": len(files),
        "malicious": find_decisive_malicious_source(files),
        "fingerprints": find_benchmark_emulation_fingerprints(files),
        "review_leads": find_source_review_leads(files),
        "generator_ngrams": ngram.report(root),
    }


def keys(findings: list[dict]) -> set[tuple[str, str]]:
    return {(f.get("kind", "?"), loc.get("path", "?")) for f in findings for loc in f.get("locations", [])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tree", type=Path)
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = {"tree": scan(args.tree)}
    if args.ref:
        result["ref"] = scan(args.ref)
    for name in result:
        r = result[name]
        print(f"## {name}: {args.tree if name == 'tree' else args.ref} ({r['files']} files)")
        for part in ("malicious", "fingerprints", "review_leads"):
            kinds = Counter(f.get("kind", "?") for f in r[part])
            print(f"  {part}: {len(r[part])} {dict(kinds) if kinds else ''}")
        g = r["generator_ngrams"]
        print(f"  generator n-gram leads: {json.dumps(g)[:400]}")
    if args.ref:
        ref_keys = {part: keys(result["ref"][part]) for part in ("malicious", "fingerprints", "review_leads")}
        print("## leads in the tree, inherited (same kind, same file in the reference) or new")
        for part in ("malicious", "fingerprints", "review_leads"):
            for f in result["tree"][part]:
                where = [(loc.get("path"), loc.get("line"), loc.get("role")) for loc in f.get("locations", [])]
                tag = "inherited" if all((f.get("kind"), p) in ref_keys[part] for p, _, _ in where) else "NEW"
                print(f"  [{tag}] {part}: {f.get('kind')} {f.get('severity', '')} {where}")
    if args.out:
        args.out.write_text(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
