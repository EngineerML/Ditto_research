"""How often a question form occurs per pack / v18 seed set (free): the narrow form (ends with these days / now / currently)
and the broad form (any "Which <plural> does ... ?" without a count word).

    python3 -I practice/qv_form_reach.py FILE.json [...]
"""
import json, re, sys, collections
NARROW = re.compile(r"^\s*Which [a-zé][\w'é -]*?s does (?!.*\b(?:two|three|four|both)\b).+?\b(?:these days|now|currently|at the moment)\?\s*$", re.I)
BROAD = re.compile(r"^\s*Which [a-zé][\w'é -]*?s does (?!.*\b(?:two|three|four|both)\b)[^?]+\?\s*$", re.I)
tot = collections.Counter()
for path in sys.argv[1:]:
    d = json.load(open(path))
    cases = d.get("memory_cases") or d.get("cases") or []
    n = sum(1 for c in cases if NARROW.search(c["question"]))
    b = sum(1 for c in cases if BROAD.search(c["question"]))
    tot["cases"] += len(cases); tot["narrow"] += n; tot["broad"] += b
    if n or b:
        ex = [c["question"] for c in cases if BROAD.search(c["question"]) and not NARROW.search(c["question"])][:2]
        print(f"{path.rsplit('/', 2)[-2] + '/' + path.rsplit('/', 1)[-1]:42} cases {len(cases):4} narrow {n:3} broad {b:3} {ex}")
print(dict(tot))
