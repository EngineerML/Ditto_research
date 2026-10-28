"""Pair every v14 memory question of the run with the agent's final answer from its trajectory, plus the
score the run's scorer gave it, as JSONL for the Go regrader."""
import difflib
import json
import re

RUN = "/home/bittensor/ditto/practice/20261028T014512Z_ditto-harness-combined-v5g_full"
V14 = json.load(open("/home/bittensor/ditto/.cache/datasets/v14_s3555973218589394111_salt0_full.json"))
rep = json.load(open(RUN + "/report.json"))["report"]
traces = [json.loads(line) for line in open(RUN + "/trace.jsonl")]
cases = {c["id"]: c for c in V14["memory_cases"]}


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s or "").lower())).strip()


norm_traces = [(norm(t["user_input"]), t) for t in traces]
with open("/tmp/regrade/pairs.jsonl", "w") as out:
    for pc in rep["per_case"]:
        if pc.get("kind") == "tool" or pc["case_id"] not in cases:
            continue
        c = cases[pc["case_id"]]
        q = norm(c["question"])
        ratio, t = max(((difflib.SequenceMatcher(None, nt, q).ratio(), t) for nt, t in norm_traces), key=lambda x: x[0])
        out.write(json.dumps({"case": c, "final_text": t.get("final_text") or "", "answer": t.get("answer") or "",
                              "run_score": float(pc["score"]), "match": round(ratio, 3)}) + "\n")
print("pairs written")
