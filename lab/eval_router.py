"""Lane routing of Hades v6, dan0l v24 and our harness on the same datasets, judged by what each case needs.

    bash lab/run.sh lab.eval_router --seeds 3590624429364033488,3135857511817419093 [--show 40] [--out FILE]

What a case needs, from its answer key:
- a memory question needs the records lane;
- a tool case whose expected calls include anything but memory reads and saves needs the action lane;
- a save, update or delete of a memory needs the action lane, or our records-lane statement path, which saves
  without a recall search first (Hades and dan0l run a recall search in the records lane, an extra call);
- a tool case expecting only memory reads, or no call at all, can be answered from either lane.

dan0l runs in its own process (lab.route_dan0l) because it and Hades both ship a package named `app`.
Embeddings: one per question, cached; no chat calls.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import subprocess
import sys
import tempfile

from lab import data, hades
from lab.embed import Embedder
from lab.eval_routing import BankRouter, bank
from lab.meaning import Meaning

SAVES = frozenset({"save_memory", "update_memory", "delete_memory"})
EITHER = frozenset({"records", "action"})


def our_lane_module():
    spec = importlib.util.spec_from_file_location("ours_lane", data.ROOT / "harness" / "app" / "routing" / "lane.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def needs(case: data.Case) -> tuple[frozenset[str], str]:
    """(acceptable lanes, kind of need)."""
    if case.phase == "memory":
        return frozenset({"records"}), "memory"
    names = set(case.tools)
    if not names:
        return EITHER, "no call"
    if names <= data.MEMORY_READS:
        return EITHER, "memory read"
    if names <= data.MEMORY_READS | SAVES:
        return frozenset({"action", "records:statement"}), "memory write"
    return frozenset({"action"}), "tool"


def judged(pick: str, ok: frozenset[str]) -> bool:
    lane = pick.split(":")[0]
    return pick in ok or lane in ok


def hades_paths(case: data.Case, lane, worlds) -> str:
    sel = hades.select(case, lane, worlds)
    return sel.path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], required=True)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--top", type=int, default=25, help="most common misses listed per system")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        dan0l_out = tmp.name
    subprocess.run([sys.executable, "-m", "lab.route_dan0l", dan0l_out, *map(str, args.seeds)], check=True, cwd=data.ROOT)
    dan0l = json.load(open(dan0l_out))
    ours_out = dan0l_out.replace(".json", "_ours.json")
    subprocess.run([sys.executable, "-m", "lab.route_ours", ours_out, *map(str, args.seeds)], check=True, cwd=data.ROOT)
    variants = json.load(open(ours_out))
    ours_lane = our_lane_module()
    embedder = Embedder(0.05)
    meaning = Meaning(embedder)
    router = BankRouter(meaning, bank(), 5)
    rows: list[dict] = []
    for seed in args.seeds:
        cases = data.load(seed)
        worlds = hades.HadesWorld()
        meaning.queries([c.text for c in cases])
        for case in cases:
            ok, need = needs(case)
            rules = hades.route(case, worlds)
            h_pick = f"{rules.name}:{rules.reason}"
            sense, sure = router(case.text)
            o_pick = h_pick
            if sure >= 0.8 and sense != rules.name:
                o_pick = ("records:statement" if ours_lane.tells_without_asking(case.text) else "records:meaning") if sense == "records" else "action:meaning"
            d = dan0l[case.key]
            d_pick = f"{d['lane']}:{d['reason']}"
            rows.append({"seed": seed, "key": case.key, "phase": case.phase, "kind": case.kind, "text": case.text, "need": need,
                         "ok": sorted(ok), "tools": list(case.tools), "hades": h_pick, "ours": o_pick, "dan0l": d_pick,
                         "dan0l_path": d["path"], "hades_path": hades_paths(case, rules, worlds), "sense": sense, "sure": round(sure, 3),
                         **{f"ours:{name}": picks[case.key] for name, picks in variants.items()}})
    systems = ("hades", "dan0l", "ours", *(f"ours:{name}" for name in variants))
    print(f"{len(rows)} cases over seeds {args.seeds}; embeddings ${embedder.spent:.5f}")
    for name in systems:
        right = [judged(r[name], frozenset(r["ok"])) for r in rows]
        per_seed = collections.defaultdict(lambda: [0, 0])
        per_need = collections.defaultdict(lambda: [0, 0])
        for r, good in zip(rows, right):
            per_seed[r["seed"]][0] += good
            per_seed[r["seed"]][1] += 1
            per_need[r["need"]][0] += good
            per_need[r["need"]][1] += 1
        print(f"\n== {name}: {sum(right)}/{len(rows)} = {sum(right) / len(rows):.4f}")
        print("   by seed: " + "  ".join(f"{s % 100000}:{a}/{b}" for s, (a, b) in per_seed.items()))
        print("   by need: " + "  ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(per_need.items())))
        misses = collections.Counter((r["need"], r["kind"], r[name]) for r, good in zip(rows, right) if not good)
        for (need, kind, pick), count in misses.most_common(args.top):
            print(f"   miss x{count:<2d} {need:12s} {kind:42s} -> {pick}")
    if args.show:
        print("\n== misrouted by any system")
        shown = 0
        for r in rows:
            wrong = [name for name in ("hades", "dan0l", "ours") if not judged(r[name], frozenset(r["ok"]))]
            if wrong and shown < args.show:
                shown += 1
                print(f"  [{','.join(wrong)}] {r['need']}/{r['kind']} H={r['hades']} O={r['ours']} D={r['dan0l']} sense={r['sense']}:{r['sure']} | {r['text'][:150]}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=0)
        print(f"rows -> {args.out}")


if __name__ == "__main__":
    main()
