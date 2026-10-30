#!/usr/bin/env python3
"""Check which SN118 kings have released their source, and catch releases that come before the
promised embargo time. Run by the Claude routine sn118-king-release-watch; safe to run by hand.

    python3 tools/release_watch.py

Candidates are the top 25 leaderboard entries, their submission-family members, and anything
still pending in the state file. The public artifact endpoint answers 425 while a king is held
("embargoed until <time>" or "awaiting confirmed winner emissions"), 200 once it is released, and
404 for agents that never held the crown. Only metadata is read here: nothing is downloaded.
State (last status and promised time per agent) lives in .cache/release_watch/state.json.
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

API = "https://platform-api.heyditto.ai"
ROOT = "/home/bittensor/ditto"
STATE = f"{ROOT}/.cache/release_watch/state.json"


def get(path):
    out = subprocess.run(["curl", "-sS", "--max-time", "30", "-w", "\n%{http_code}", API + path],
                         capture_output=True, text=True)
    body, _, code = out.stdout.rpartition("\n")
    return code, body


def parse_time(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


now = dt.datetime.now(dt.timezone.utc)
stamp = now.isoformat(timespec="seconds")
state = json.load(open(STATE)) if os.path.exists(STATE) else {}

code, body = get("/api/v1/public/leaderboard")
if code != "200":
    raise SystemExit(f"leaderboard fetch failed: HTTP {code} {body[:200]}")
board = json.loads(body)
champion = board["emissions"].get("champion_agent_id")

candidates = {}
for e in board["entries"][:25]:
    candidates[e["agent_id"]] = f'{e["agent_name"]}-v{e["agent_version"]}'
    for m in (e.get("submission_family") or {}).get("members", []):
        candidates.setdefault(m["agent_id"], f'{m["agent_name"]}-v{m["agent_version"]}')
for agent, s in state.items():
    if s["status"] != "released":
        candidates.setdefault(agent, s["label"])

# released/<label>_<first 8 of id>, written by tools/fetch_release.sh
downloaded = {os.path.basename(p).rsplit("_", 1)[-1] for p in glob.glob(f"{ROOT}/released/*_*")}

with ThreadPoolExecutor(8) as pool:
    answers = dict(zip(candidates, pool.map(lambda a: get(f"/api/v1/public/agent/{a}/artifact"), candidates)))

events, pending, errors = [], [], []
for agent, label in candidates.items():
    code, body = answers[agent]
    if code == "404":
        continue
    old = state.get(agent, {})
    s = {"label": label, "first_seen": old.get("first_seen", stamp), "checked": stamp}
    if code == "200":
        s["status"] = "released"
        s["released_seen"] = old.get("released_seen") or stamp
        s["promised"] = old.get("promised")
        if old.get("status") != "released" or agent[:8] not in downloaded:
            early = ""
            if s["promised"] and parse_time(s["promised"]) > now:
                early = f", {(parse_time(s['promised']) - now).total_seconds() / 3600:.1f} h EARLIER than promised {s['promised']}"
            elif s["promised"]:
                early = f", promised {s['promised']}"
            have = "already downloaded" if agent[:8] in downloaded else "NOT downloaded yet"
            events.append(f"RELEASED {label} {agent}{early}; {have}")
    elif code == "425":
        msg = json.loads(body).get("message", body)
        m = re.search(r"embargoed until (\S+)", msg)
        s["status"] = "embargoed" if m else "awaiting_emissions"
        s["promised"] = m.group(1) if m else None
        if old.get("promised") and s["promised"] and s["promised"] != old["promised"]:
            events.append(f"MOVED {label} {agent}: promised {old['promised']} -> {s['promised']}")
        elif old and old.get("status") != s["status"]:
            events.append(f"STATUS {label} {agent}: {old.get('status')} -> {s['status']}")
        elif not old:
            events.append(f"NEW KING CANDIDATE {label} {agent}: {s['status']} {s['promised'] or ''}".rstrip())
        pending.append(s | {"agent": agent})
    else:
        errors.append(f"{label} {agent}: HTTP {code} {body[:150]}")
        continue
    state[agent] = s

os.makedirs(os.path.dirname(STATE), exist_ok=True)
with open(STATE + ".tmp", "w") as f:
    json.dump(state, f, indent=1, sort_keys=True)
os.replace(STATE + ".tmp", STATE)

print(f"checked {stamp}: {len(candidates)} candidates, champion {candidates.get(champion, '?')} {champion}")
print("events:" if events else "events: none")
for line in events:
    print("  " + line)
print("still held:")
for s in sorted(pending, key=lambda s: s["promised"] or "9999"):
    print(f"  {s['label']:<22} {s['agent']}  {s['promised'] or 'awaiting confirmed winner emissions'}")
for line in errors:
    print("ERROR " + line)
