"""Record selection of dan0l v24 and our harness on the same datasets: recall, precision and size.

    bash lab/run.sh lab.compare_selection --seeds 3590624429364033488,... [--out FILE]

Each case's needed records are its answer key's evidence (memory questions: the labelled
evidence pairs; tool cases: the records holding a required argument). Recall is the share of
needed records shown to the deciding model, precision the share of shown records that are
needed, full recall the share of cases with every needed record shown. Only cases with
labelled evidence count. Both selections leave out the recall turn's pins.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import subprocess
import sys
import tempfile

from lab import data

SYSTEMS = (("dan0l", "lab.select_dan0l"), ("ours", "lab.select_ours"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    picks = {}
    for name, module in SYSTEMS:
        with tempfile.NamedTemporaryFile(suffix=f"_{name}.json", delete=False) as tmp:
            path = tmp.name
        subprocess.run([sys.executable, "-m", module, path, *map(str, args.seeds)], check=True, cwd=data.ROOT)
        picks[name] = json.load(open(path))
    rows = []
    for seed in args.seeds:
        for case in data.load(seed):
            if not case.needs:
                continue
            row = {"key": case.key, "phase": case.phase, "kind": case.kind, "needs": len(case.needs), "text": case.text}
            for name, _ in SYSTEMS:
                p = picks[name][case.key]
                shown = set(p["ids"])
                hit = len(case.needs & shown)
                row[name] = {"path": p["path"], "recall": hit / len(case.needs), "full": hit == len(case.needs),
                             "precision": hit / len(shown) if shown else 0.0, "records": len(shown), "chars": p["chars"],
                             "missing": sorted(case.needs - shown)}
            rows.append(row)

    def report(label: str, subset: list[dict]) -> None:
        if not subset:
            return
        print(f"\n== {label}: {len(subset)} cases")
        for name, _ in SYSTEMS:
            m = [r[name] for r in subset]
            print(f"   {name:6s} recall {statistics.mean(x['recall'] for x in m):.3f}  full {statistics.mean(x['full'] for x in m):.3f}  "
                  f"precision {statistics.mean(x['precision'] for x in m):.3f}  records {statistics.mean(x['records'] for x in m):5.1f}  "
                  f"chars {statistics.mean(x['chars'] for x in m):7.0f}")

    report("all cases with evidence", rows)
    for phase in ("memory", "tool"):
        report(phase, [r for r in rows if r["phase"] == phase])
    for name, _ in SYSTEMS:
        for path in sorted({r[name]["path"] for r in rows}):
            report(f"{name} path={path}", [r for r in rows if r[name]["path"] == path])
    print("\n== memory kinds where full recall differs (dan0l vs ours)")
    kinds = collections.defaultdict(list)
    for r in rows:
        if r["phase"] == "memory":
            kinds[r["kind"]].append(r)
    for kind, rs in sorted(kinds.items(), key=lambda kv: statistics.mean(r["ours"]["full"] for r in kv[1]) - statistics.mean(r["dan0l"]["full"] for r in kv[1])):
        d = statistics.mean(r["dan0l"]["full"] for r in rs)
        o = statistics.mean(r["ours"]["full"] for r in rs)
        if abs(d - o) > 1e-9:
            print(f"   {kind:42s} n={len(rs):3d}  full dan0l {d:.2f}  ours {o:.2f}  chars dan0l {statistics.mean(r['dan0l']['chars'] for r in rs):6.0f}  ours {statistics.mean(r['ours']['chars'] for r in rs):6.0f}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=0)
        print(f"rows -> {args.out}")


if __name__ == "__main__":
    main()
