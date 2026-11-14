"""Run a harness's tied-names view offline over a generator pack: no model, no network.

For each case it builds the harness's UserIndex from the case user's stored pairs (as the scorer seeds them),
calls tied_names_view(question, index) and reports whether the view fired, the ties it found, and whether
every gold item and any distractor appear in what it shows.

    .venv/bin/python tools/tied_view_probe.py HARNESS_DIR PACK.json [--show NAME]
"""
import argparse
import importlib
import json
import re
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("harness")
    ap.add_argument("pack")
    ap.add_argument("--show", default="", help="print the view for questions containing this text")
    args = ap.parse_args()
    sys.path.insert(0, args.harness)
    protocol = importlib.import_module("app.protocol")
    retrieval = importlib.import_module("app.memory.retrieval")
    evidence = importlib.import_module("app.evidence")
    pack = json.load(open(args.pack))
    stores: dict[str, list] = {}
    for wave in pack["memory_waves"]:
        for p in wave["pairs"]:
            stores.setdefault(wave.get("user_id") or p.get("user_id") or "", []).append(protocol.MemoryPair(**{k: p[k] for k in ("pair_id", "session_id", "timestamp", "prompt", "response") if k in p}))
    indexes = {user: retrieval.UserIndex(pairs) for user, pairs in stores.items()}
    fired = full = 0
    for case in pack["cases"]:
        view = evidence.tied_names_view(case["question"], (indexes.get(case.get("user_id") or "") or next(iter(indexes.values()))))
        shown = view.shown if view else ""
        gold = case.get("answer_items") or []
        got = sum(1 for item in gold if item in shown)
        bad = [d for d in case.get("distractor_answers") or [] if d in shown]
        fired += view is not None
        full += bool(view) and got == len(gold)
        if not view or got < len(gold) or (args.show and args.show in case["question"]):
            ties = re.search(r"\(([^)]*= [^)]*)\)", shown)
            print(f"{'VIEW' if view else 'none'} gold {got}/{len(gold)} distractors {len(bad)} | {case['question']} | ties: {ties.group(1) if ties else '-'}")
            if args.show and args.show in case["question"]:
                print(shown)
    print(f"cases {len(pack['cases'])}: view fired {fired}, all gold shown {full}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
