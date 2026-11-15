import json, sys
d = json.load(open(sys.argv[1]))
w = d["memory_waves"]
print(type(w), len(w))
for x in w[:3]:
    print(type(x), (sorted(x) if isinstance(x, dict) else (type(x[0]), sorted(x[0]) if isinstance(x[0], dict) else x[0])))
