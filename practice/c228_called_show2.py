"""Changed non-datagen, non-fq pack cases: question, gold, new tie, the record giving it."""
import json, re
a = json.load(open("/tmp/c228_called_old.json")); b = json.load(open("/tmp/c228_called_new.json"))
for k in [k for k in b if a.get(k) != b[k] and not k.split(":")[0].isdigit() and not k.startswith("fq-v2")]:
    path, cid = k.split(":")
    d = json.load(open(f"/home/bittensor/ditto/.cache/miner_gens/packs/{path}"))
    c = next(c for c in d["cases"] if c["id"] == cid)
    new = [r for r in b[k] if r not in (a.get(k) or [])]
    print(f"\n== {k} Q: {c['question']}\n   gold: {c['expected_answer']} | old {a.get(k)} | new {new}")
    for r in new[:1]:
        full, alias = r[1], r[2]
        for w in d["memory_waves"]:
            for p in w.get("pairs") or []:
                if re.search(r"\b" + re.escape(alias) + r"\b", p["prompt"]) and full in p["prompt"]:
                    s = [x for x in re.split(r"(?<=[.!?])\s+", p["prompt"]) if alias in x]
                    print(f"   REC ({len(p['prompt'])} chars):", s[0][:250] if s else p["prompt"][:250])
