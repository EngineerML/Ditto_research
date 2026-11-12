import json, sys, glob, os, subprocess
d = sys.argv[1].rstrip("/") + "/"
B = "https://platform-api.heyditto.ai/api/v1/public/agent/"
subprocess.run(["curl", "-s", "--max-time", "30", B + "2be324cc-23ec-4810-a72d-e5f145b3b614/scores", "-o", d + "scores_overhorizoner_2.json"])
for f in sorted(glob.glob(d + "scores_*.json")):
    s = json.load(open(f))
    for r in s.get("scores", [])[:4]:
        bd = r.get("dueling_breakdown") or {}
        cs = " ".join(f"{c['column_id']}={c['mean']:.2f}(b{c['grading_bench_version']})" for c in bd.get("columns", []))
        print(f"{os.path.basename(f)[7:-5]:16} s{bd.get('season_index')} comp {r['composite']:.3f} dg {bd.get('datagen_raw') or 0:.3f} gate {bd.get('datagen_gate')} gsum {bd.get('generator_sum') or 0:.3f} | {cs}")
