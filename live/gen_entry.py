"""Dump one generator board entry (by submission prefix) from a snapshot, plus the generator-sources API reply."""
import json, sys, subprocess
d = sys.argv[1].rstrip("/") + "/"
pre = sys.argv[2]
for g in json.load(open(d + "generator_board.json"))["entries"]:
    if g["submission_id"].startswith(pre):
        print(json.dumps(g, indent=1)[:5000])
        sid = g["submission_id"]
        break
else:
    sid = None
    print("not on the generator board")
if sid:
    r = subprocess.run(["curl", "-s", "--max-time", "30", f"https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/{sid}"], capture_output=True, text=True)
    print("generator-sources:", r.stdout[:1500])
