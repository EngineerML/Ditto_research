"""Program replies of practice runs, joined to their case and graded offline with grade_replies.

    python3 practice/gates/grader_probe/program_replies.py LABEL [LABEL ...]

For each bench-14 run of the labels: every program case of the report, its trace (found by the question's case-file
token and wording), and the reply the harness served. Prints how often the offline grade agrees with the scorer's.
Importable: replies(labels) and grade(rows)."""
import difflib
import glob
import json
import re
import subprocess
import sys

ROOT = "/home/bittensor/ditto"
GRADER = f"{ROOT}/practice/gates/grader_probe/grade_replies/grade_replies"
PROGRAM = ("v13-open-program", "v13-personal-program")
SCOPE_RE = re.compile(r"\bc[0-9a-f]{16}\b")


def dataset(seed: int) -> dict[str, dict]:
    data = json.load(open(f"{ROOT}/.cache/datasets/v14_s{seed}_salt0_full.json"))
    return {c["id"]: c for c in data["memory_cases"] if c["question_type"] in PROGRAM}


def replies(labels: list[str]) -> list[dict]:
    rows = []
    for run in sorted(glob.glob(f"{ROOT}/practice/2026*_ditto-harness-*_full*")):
        label = re.search(r"ditto-harness-(.+?)_full", run).group(1)
        if label not in labels:
            continue
        try:
            rep = json.load(open(f"{run}/report.json"))
            traces = [json.loads(line) for line in open(f"{run}/trace.jsonl")]
        except (OSError, ValueError):
            continue
        if rep.get("bench_version") != 14:
            continue
        seed = int(rep["seed"])
        known = dataset(seed)
        for c in rep["report"]["per_case"]:
            cid = c["case_id"].rsplit("/", 1)[-1]
            case = known.get(cid)
            if case is None:
                continue
            scope = SCOPE_RE.search(case["question"])
            found = [t for t in traces if scope and scope.group(0) in t["user_input"]]
            if not found:
                continue
            t = max(found, key=lambda t: difflib.SequenceMatcher(None, t["user_input"], case["question"]).ratio())
            rows.append({"label": label, "run": run, "seed": seed, "id": cid, "score": c["score"], "answer": t.get("answer") or "",
                         "final_text": t.get("final_text") or "", "question": t["user_input"], "expected": case["expected_answer"]})
    return rows


def grade(rows: list[dict]) -> list[dict]:
    lines = "".join(json.dumps({"seed": r["seed"], "id": r["id"], "answer": r["answer"], "final_text": r["final_text"]}) + "\n" for r in rows)
    out = subprocess.run([GRADER], input=lines, capture_output=True, text=True, check=True).stdout.splitlines()
    return [json.loads(line) for line in out]


if __name__ == "__main__":
    rows = replies(sys.argv[1:])
    graded = grade(rows)
    agree = sum(1 for r, g in zip(rows, graded) if g["found"] and (g["score"] >= 0.5) == (r["score"] >= 0.5))
    exact = sum(1 for r, g in zip(rows, graded) if g["found"] and abs(g["score"] - r["score"]) < 1e-6)
    print(f"{len(rows)} replies, {sum(g['found'] for g in graded)} cases found; right/wrong agrees {agree}, exact score {exact}")
    for r, g in zip(rows, graded):
        if g["found"] and (g["score"] >= 0.5) != (r["score"] >= 0.5):
            print(f"  scorer {r['score']:.2f} offline {g['score']:.2f} {r['label']} exp={r['expected'][:40]!r} ans={r['answer'][:40]!r} notes={g['notes'][:2]}")
