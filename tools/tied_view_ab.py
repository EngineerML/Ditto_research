"""Offline A/B of two harness trees' tied-names view over generator packs: no model, no network.

For each pack it counts, per tree, the cases where the view fires, where it shows every gold item, and where what it
shows (or its code-read list) names a distractor, a look-alike's item or another case's item.

    .venv/bin/python tools/tied_view_ab.py A_DIR B_DIR PACK_DIR [PACK_DIR ...]
"""
import glob
import importlib
import json
import sys


def load(tree):
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.path.insert(0, tree)
    mods = (importlib.import_module("app.protocol"), importlib.import_module("app.memory.retrieval"), importlib.import_module("app.evidence"))
    sys.path.remove(tree)
    return mods


def measure(tree, packs):
    protocol, retrieval, evidence = load(tree)
    out = {}
    for pack_dir in packs:
        fired = gold_all = bad_view = bad_list = n = 0
        for f in sorted(glob.glob(pack_dir + "/*.json")):
            pack = json.load(open(f))
            stores = {}
            for w in pack["memory_waves"]:
                for p in w["pairs"]:
                    stores.setdefault(w.get("user_id") or p.get("user_id") or "", []).append(
                        protocol.MemoryPair(**{k: p[k] for k in ("pair_id", "session_id", "timestamp", "prompt", "response") if k in p}))
            idx = {u: retrieval.UserIndex(ps) for u, ps in stores.items()}
            all_items = {i for c in pack["cases"] for i in (c.get("answer_items") or [])}
            for c in pack["cases"]:
                n += 1
                v = evidence.tied_names_view(c["question"], idx.get(c.get("user_id") or "") or next(iter(idx.values())))
                if not v:
                    continue
                fired += 1
                gold = c.get("answer_items") or []
                gold_all += all(g in v.shown for g in gold)
                wrong = set(c.get("distractor_answers") or []) | (all_items - set(gold))
                listed = v.shown.split("Code read off", 1)[1] if "Code read off" in v.shown else ""
                notes = v.shown.split("Code read off", 1)[0]
                bad_view += any(w in notes for w in wrong)
                bad_list += any(w in listed for w in wrong)
        out[pack_dir.rstrip("/").split("/")[-1]] = (n, fired, gold_all, bad_view, bad_list)
    return out


if __name__ == "__main__":
    a, b, packs = sys.argv[1], sys.argv[2], sys.argv[3:]
    ra, rb = measure(a, packs), measure(b, packs)
    print(f"{'pack':24} {'n':>4} | {'A fired':>7} {'A gold':>6} {'A wrong-in-view':>15} | {'B fired':>7} {'B gold':>6} {'B wrong-in-view':>15} {'B wrong-in-list':>15}")
    for k in ra:
        n, fa, ga, wa, _ = ra[k]
        _, fb, gb, wb, lb = rb[k]
        print(f"{k:24} {n:>4} | {fa:>7} {ga:>6} {wa:>15} | {fb:>7} {gb:>6} {wb:>15} {lb:>15}")
