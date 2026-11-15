"""Results of practice/c228_v6_test.sh: per-pack reply shapes for A, and the full run summary for B."""
import json, glob, re, os
G = sorted(glob.glob("/home/bittensor/ditto/practice/generator/2026*Z"))[-1]
DECLINE = re.compile(r"no record|not stated|not found|couldn'?t find|can'?t find|unknown|no other|only one|don'?t have|isn'?t in|there is no|not sure", re.I)
print("A:", G)
for pack in ("memgen-v6-hidden", "memgen-v6", "fq-v2-2"):
    p = json.load(open(f"{G}/packs/{pack}.json"))
    byq = {c["question"]: c for c in p["cases"]}
    n = dec = one = both = ok = 0
    for line in open(f"{G}/trace/{pack}-r0/v6/trace.jsonl"):
        t = json.loads(line)
        c = byq.get(t["user_input"])
        if not c:
            continue
        n += 1
        reply = t.get("final_text") or ""
        dec += bool(DECLINE.search(reply))
        items = c.get("answer_items") or [c["expected_answer"]]
        got = sum(1 for i in items if i.lower() in reply.lower())
        one += got == 1
        both += got >= 2
        ok += got >= 1
    print(f"  {pack:18} cases {n}  decline-phrase {dec:2}  named 1 {one:2}  named 2+ {both:2}  named gold {ok}")
R = "/home/bittensor/ditto/practice/20261115T080014Z_ditto-harness-c228fx2t_full"
print("B:", R, sorted(os.listdir(R)))
for f in sorted(glob.glob(R + "/*.json")):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    if isinstance(d, dict):
        keys = {k: d[k] for k in d if isinstance(d[k], (int, float, str)) and k not in ("run_id",)}
        print(" ", os.path.basename(f), json.dumps(keys)[:900])
        res = d.get("case_results") or d.get("results") or []
        if isinstance(res, list) and res:
            low = [r for r in res if isinstance(r, dict) and (r.get("score") or 0) < 1]
            print("   cases", len(res), "below 1:", len(low))
            for r in low[:12]:
                print("    ", r.get("category"), r.get("kind"), r.get("score"), str(r.get("notes"))[:120])
