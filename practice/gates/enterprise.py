"""Enterprise-composed-program cases of the v8 s45 runs and v6's s42 runs: scores by twin group, with answers."""
import glob, json, re, difflib
from collections import defaultdict
for run in sorted(glob.glob("/home/bittensor/ditto/practice/2026*_ditto-harness-v8_full_rerun") + glob.glob("/home/bittensor/ditto/practice/20261031T03*_ditto-harness-v6-hold_full_rerun")):
    rep = json.load(open(run + "/report.json"))
    cases = rep["report"]["per_case"]
    if len(cases) < 200:
        continue
    seed = int(rep["seed"])
    data = {c["id"]: c for c in json.load(open(f"/home/bittensor/ditto/.cache/datasets/v14_s{seed}_salt0_full.json"))["memory_cases"]}
    traces = [json.loads(l) for l in open(run + "/trace.jsonl")]
    groups = defaultdict(list)
    for c in cases:
        if c["category"] == "enterprise-composed-program":
            d = data[c["case_id"].rsplit("/", 1)[-1]]
            groups[d.get("twin_group")].append((c, d))
    print(run.split("/")[-1][:45], seed)
    for g, members in groups.items():
        scores = [c["score"] for c, _ in members]
        flag = "SPLIT" if any(s >= 0.5 for s in scores) and any(s < 0.5 for s in scores) else ""
        print(f"   group {g} scores {scores} {flag} expected {members[0][1]['expected_answer']!r}")
        if flag:
            for c, d in members:
                scope = re.search(r"c[0-9a-f]{16}", d["question"]).group(0)
                t = max((t for t in traces if scope in t["user_input"]), key=lambda t: difflib.SequenceMatcher(None, t["user_input"], d["question"]).ratio())
                print(f"      {c.get('relation')} {c['score']} path={t.get('path')} ans={t.get('answer')!r} q={t['user_input'][40:140]!r}")
