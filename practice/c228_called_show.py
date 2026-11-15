"""Show the datagen cases whose called-name result changed: question, gold, and the records holding the alias."""
import json, re
a = json.load(open("/tmp/c228_called_old.json")); b = json.load(open("/tmp/c228_called_new.json"))
for k in [k for k in b if a.get(k) != b[k] and k.split(":")[0].isdigit()]:
    seed, cid = k.split(":")
    d = json.load(open(f"/home/bittensor/ditto/.cache/v18sets/{seed}.json"))
    c = next(c for c in d["memory_cases"] if c["id"] == cid)
    print(f"\n== {k} [{c['question_type']}] Q: {c['question']}\n   gold: {c['expected_answer']} | new tie {b[k]}")
    full, alias = [r for r in b[k] if r not in (a.get(k) or [])][0][1:3]
    for w in d["memory_waves"]:
        for p in w.get("pairs") or []:
            if re.search(r"\b" + re.escape(alias) + r"\b", p["prompt"]) and re.search(r"\b" + re.escape(full.split()[0]) + r"\b", p["prompt"]):
                print("   REC:", p["prompt"][:300].replace("\n", " "))
