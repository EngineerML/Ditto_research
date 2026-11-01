import json, re
def items(text):
    text = (text or "").lower().replace(" ", " ").replace("‑", "-")
    parts = re.split(r"\s*[;,]\s*|\s+[–—-]\s+|\s+and\s+", text)
    return sorted(p for p in (re.sub(r"\s+", " ", re.sub(r"^[\W_]+|[\W_]+$", "", x)).strip() for x in parts) if p)
a = json.load(open("/home/bittensor/ditto/practice/gates/s44/replay_v71.json"))
b = json.load(open("/home/bittensor/ditto/practice/gates/s44/replay_v71b.json"))
print(len(b), "re-replayed")
for j in b:
    same = items(j["new"]) == items(j["old"])
    ok = items(j["new"]) == items(j["expected"])
    print(f"{'same' if same else 'DIFF'} {'ok' if ok else '  '} graded-old={j['graded']} {j['label'][:30]:30} exp={j['expected'][:38]!r} old={j['old'][:38]!r} new={j['new'][:45]!r}")
