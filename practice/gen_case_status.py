"""Per-family case status (discriminating / trivial / unsolved) and credit in a generator panel run, from the
scorer's own result (run-*.json), plus its pack score.
    python3 practice/gen_case_status.py RUN_DIR
"""
import json, glob, sys, collections
run = sys.argv[1]
for rf in sorted(glob.glob(f"{run}/run-*.json")):
    sc = json.load(open(rf))["score"]
    for s in sc["seeds"]:
        fam = collections.defaultdict(collections.Counter)
        for c in s["cases"]:
            f = c["case_id"].rsplit("-", 1)[0]
            fam[f][c["status"]] += 1
            fam[f]["credit"] += c["credit"]
        for f in sorted(fam):
            print(f"{f:30s} disc {fam[f]['discriminating']}  triv {fam[f]['trivial']}  uns {fam[f]['unsolved']}"
                  f"  credit {fam[f]['credit']:.2f}")
        print(f"{rf.rsplit('/', 1)[1]}: score {s['score']:.3f}  disc {s['discriminating']}  triv {s['trivial']}"
              f"  uns {s['unsolved']}  credit {s['raw_credit']:.2f}")
