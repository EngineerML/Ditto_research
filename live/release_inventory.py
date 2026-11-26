"""Every released SN118 agent and generator source, and which of them are not downloaded yet.

Sources of ids: all live/ snapshots (activity, leaderboard, generator boards incl. 'recent', dueling pins/sources)
and the release-watch state. Status comes from the public artifact / generator-source endpoints (metadata only).
    python3 -I live/release_inventory.py [--json OUT]
Prints MISSING lines: kind, id, label, released time. Nothing is downloaded or run here.
"""
import glob, json, os, re, subprocess, sys

ROOT = "/home/bittensor/ditto"
API = "https://platform-api.heyditto.ai/api/v1"


def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


def curl(url):
    out = subprocess.run(["curl", "-s", "--max-time", "30", "-w", "\n%{http_code}", url], capture_output=True, text=True).stdout
    body, _, code = out.rpartition("\n")
    try:
        return int(code), json.loads(body)
    except Exception:
        return int(code or 0), {"raw": body[:200]}


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(text or "unnamed")).strip("-") or "unnamed"


agents, gens = {}, {}
for snap in sorted(glob.glob(f"{ROOT}/live/2026-*")):
    act = load(f"{snap}/public_activity_limit_200.json") or {}
    for e in act.get("entries", []):
        agents.setdefault(e["agent_id"], (e.get("name"), e.get("version")))
    lb = load(f"{snap}/public_leaderboard.json") or {}
    for e in lb.get("entries", []):
        agents.setdefault(e["agent_id"], (e.get("agent_name"), e.get("agent_version")))
    gb = load(f"{snap}/generator_board.json") or {}
    for e in gb.get("entries", []):
        gens.setdefault(e["submission_id"], (e.get("name"), e.get("version")))
        for r in e.get("recent") or []:
            gens.setdefault(r["submission_id"], (e.get("name"), None))
    ds = load(f"{snap}/public_dueling_seasons.json") or {}
    for s in ds.get("seasons", []):
        cols = ((s.get("pins") or {}).get("columns") or []) + (s.get("sources") or [])
        for c in cols:
            sid = c.get("submission_id")
            if sid:
                gens.setdefault(sid, (c.get("name") or c.get("generator_name"), c.get("version") or c.get("generator_version")))
state = load(f"{ROOT}/.cache/release_watch/state.json") or {}
for aid, v in state.items():
    agents.setdefault(aid, (v.get("label"), None))

have_agents = {d.rsplit("_", 1)[-1] for d in os.listdir(f"{ROOT}/released")}
have_gens = {d.rsplit("_", 1)[-1] for d in os.listdir(f"{ROOT}/.cache/miner_gens/dl")}

from concurrent.futures import ThreadPoolExecutor


def curl_retry(url):
    for _ in range(3):
        code, m = curl(url)
        if code:
            return code, m
    return code, m


def agent_row(item):
    aid, (name, ver) = item
    if aid[:8] in have_agents:
        return {"kind": "agent", "id": aid, "name": name, "version": ver, "status": "have", "have": True}
    code, m = curl_retry(f"{API}/public/agent/{aid}/artifact")
    detail = (m.get("detail") or m.get("error") or "") if isinstance(m, dict) else ""
    status = "released" if code == 200 else f"{code} {detail}".strip()
    return {"kind": "agent", "id": aid, "name": name, "version": ver, "status": str(status)[:90], "have": False,
            "released_at": (m.get("released_at") or m.get("available_at")) if code == 200 else None,
            "bench": m.get("bench_version") if code == 200 else None}


def gen_row(item):
    sid, (name, ver) = item
    have = sid[:8] in have_gens
    code, m = curl_retry(f"{API}/public/dueling/generator-sources/{sid}")
    released = code == 200 and bool(m.get("available"))
    return {"kind": "generator", "id": sid, "name": name, "version": ver, "hotkey": m.get("miner_hotkey"),
            "status": "have" if have else ("released" if released else str(code)), "have": have, "released": released,
            "released_at": m.get("released_at"), "public_default": m.get("public_default")}


with ThreadPoolExecutor(12) as pool:
    rows = list(pool.map(agent_row, sorted(agents.items()))) + list(pool.map(gen_row, sorted(gens.items())))

missing = sorted((r for r in rows if not r["have"] and r["status"] == "released"),
                 key=lambda r: (r["kind"], str(r.get("released_at"))))
from collections import Counter
print("agents:", len(agents), Counter(r["status"][:30] for r in rows if r["kind"] == "agent").most_common(8))
print("generators:", len(gens), Counter(str(r["status"])[:30] for r in rows if r["kind"] == "generator").most_common(8))
for r in missing:
    label = f"{slug(r['name'])}-v{r['version']}" if r.get("version") is not None else slug(r["name"])
    print(f"MISSING {r['kind']} {r['id']} {label}_{r['id'][:8]} released {r.get('released_at')}")
if "--json" in sys.argv:
    json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
