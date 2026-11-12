import json, subprocess
from datetime import datetime, timedelta
B = "https://platform-api.heyditto.ai/api/v1/public/"
act = json.loads(subprocess.run(["curl", "-s", "--max-time", "30", B + "activity?limit=200"], capture_output=True, text=True).stdout)["entries"]
for e in act:
    if e["name"] in ("dan0l", "beast-d41", "Tessellate", "crown-v229", "crown-v228", "logan", "DrPresident") and e["status"] == "scored":
        r = e["artifact_release"]
        fin = r.get("finalized_at")
        eta = (datetime.fromisoformat(fin.replace("Z", "+00:00")) + timedelta(hours=r["embargo_hours"])).strftime("%m-%d %H:%M") if fin else None
        print(f"{e['name']} v{e['version']} {e['agent_id'][:8]} release {r['status']} finalized {fin and fin[:16]} +{r['embargo_hours']}h -> {eta} crowned {r.get('crowned_at') and r['crowned_at'][:16]} avail {r.get('available_at')}")
