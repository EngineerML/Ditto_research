"""Grade a running (or finished) subset run as it goes: every trace written so far, in the order it
finished, matched to its question and graded with grade.Memory (v14), then the running mean per 10.

    .venv/bin/python tools/regrade/live.py RUN_DIR SEED CASES.txt [OTHER_RUN_DIR]

With OTHER_RUN_DIR the same questions are graded for that run too and shown beside it.
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lab import data  # noqa: E402

data.BENCH = 14


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s or "").lower())).strip()


def graded(run: str, cases: dict) -> list[tuple[str, str, float]]:
    """(case id, family, score) per trace of the run, in the order the traces were written."""
    path = Path(run) / "trace.jsonl"
    traces = [json.loads(line) for line in open(path, encoding="utf-8")] if path.is_file() else []
    pending = dict(cases)
    pairs = []
    for t in traces:
        if not pending:
            break
        q = norm(t["user_input"])
        ratio, cid = max((difflib.SequenceMatcher(None, q, norm(c["question"])).ratio(), cid) for cid, c in pending.items())
        if ratio < 0.85:
            continue
        pairs.append(json.dumps({"case": pending.pop(cid), "final_text": t.get("final_text") or "", "answer": t.get("answer") or "", "run_score": -1, "match": round(ratio, 3)}))
    if not pairs:
        return []
    out = subprocess.run(["go", "run", "."], cwd=HERE, input="\n".join(pairs) + "\n", capture_output=True, text=True, check=True).stdout
    return [(r["id"], r["type"], float(r["v14"])) for r in map(json.loads, out.splitlines())]


def main() -> None:
    run, seed, wanted = sys.argv[1], int(sys.argv[2]), set(open(sys.argv[3]).read().split())
    d = json.load(open(data.dataset_path(seed, 0, "full")))
    cases = {c["id"]: c for c in d["memory_cases"] if c["id"] in wanted}
    new = graded(run, cases)
    old = {cid: s for cid, _, s in graded(sys.argv[4], cases)} if len(sys.argv) > 4 else {}
    total = paired_new = paired_old = paired = 0.0
    for i, (cid, fam, s) in enumerate(new, 1):
        total += s
        if cid in old:
            paired += 1
            paired_new += s
            paired_old += old[cid]
        if i % 10 == 0 or i == len(new):
            beside = f"  | same questions: {paired_new / paired:.3f} vs {paired_old / paired:.3f} ({int(paired)})" if paired else ""
            print(f"{i:3d}/{len(cases)}  mean {total / i:.3f}{beside}")
    misses = [(fam, cid, s) for cid, fam, s in new if s < 0.999]
    for fam, cid, s in sorted(misses):
        print(f"  miss {fam:34s} {cid} {s}{'' if cid not in old else f'  (other {old[cid]})'}")


if __name__ == "__main__":
    main()
