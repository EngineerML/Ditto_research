"""Free: datagen memory questions (4 v18 seeds) the fix 1 list note fires on, by category and answer kind."""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.guide_records import LIST_ASK_RE  # noqa: E402
hits = collections.Counter()
total = 0
ex = []
for s in (1810003, 1810004, 1810005, 1810006):
    d = json.load(open(f"/home/bittensor/ditto/.cache/v18sets/{s}.json"))
    for c in d["memory_cases"]:
        total += 1
        if LIST_ASK_RE.search(c["question"]):
            hits[(c["question_type"], c.get("answer_kind"))] += 1
            if len(ex) < 6:
                ex.append((c["question_type"], c["question"][:120], str(c["expected_answer"])[:60]))
print("fires on", sum(hits.values()), "of", total)
for k, v in hits.most_common():
    print(" ", v, k)
for e in ex:
    print("  e.g.", e)
