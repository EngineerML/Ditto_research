"""Download every released generator source and agent artifact listed as MISSING by release_inventory.py.

Each lands in its own new folder; archives are SHA-256 checked against the published value and extracted with
tarfile's 'data' filter (no links, devices, absolute paths or escapes). Nothing downloaded is executed.
    python3 -I live/fetch_missing_releases.py live/<snapshot>/release_inventory.json
"""
import hashlib, io, json, os, re, subprocess, sys, tarfile
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/bittensor/ditto"
API = "https://platform-api.heyditto.ai/api/v1"
rows = json.load(open(sys.argv[1]))
todo = [r for r in rows if not r["have"] and r["status"] == "released"]


def slug(t):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(t or "unnamed")).strip("-") or "unnamed"


def get(url, timeout=300):
    p = subprocess.run(["curl", "-sSfL", "--max-time", str(timeout), url], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"curl {p.returncode}: {p.stderr.decode()[:200]}")
    return p.stdout


def extract(blob, dest):
    os.makedirs(dest)
    with tarfile.open(fileobj=io.BytesIO(blob)) as t:
        bad = [m.name for m in t.getmembers() if m.issym() or m.islnk() or m.isdev() or m.name.startswith("/")
               or ".." in m.name.split("/")]
        if bad:
            raise RuntimeError(f"unsafe members {bad[:5]}")
        t.extractall(dest, filter="data")
    return sum(len(f) for _, _, f in os.walk(dest))


def fetch_generator(r):
    label = f"{slug(r['name'])}-v{r['version']}" if r.get("version") is not None else slug(r["name"])
    out = f"{ROOT}/.cache/miner_gens/dl/{label}_{r['id'][:8]}"
    if os.path.exists(out):
        return f"exists {out}"
    meta = json.loads(get(f"{API}/public/dueling/generator-sources/{r['id']}", 60))
    blob = get(f"{API}/public/dueling/generator-sources/{r['id']}/archive")
    sha = hashlib.sha256(blob).hexdigest()
    ok = sha == meta.get("source_sha256")
    os.makedirs(out)
    json.dump({**meta, "archive_sha256": sha, "sha_matches_source_sha256": ok}, open(f"{out}/meta.json", "w"), indent=1)
    open(f"{out}/archive.bin", "wb").write(blob)
    n = extract(blob, f"{out}/src")
    return f"{'OK ' if ok else 'SHA?'} {label}_{r['id'][:8]} {len(blob)//1024} KB {n} files"


def fetch_agent(r):
    label = f"{slug(r['name'])}-v{r['version']}_{r['id'][:8]}"
    p = subprocess.run(["bash", f"{ROOT}/tools/fetch_release.sh", r["id"], label], capture_output=True, text=True)
    tail = [l for l in p.stdout.splitlines() if l.startswith(("sha256", "SHA256", "unsafe", "total files"))]
    return f"{'OK ' if p.returncode == 0 else 'FAIL'} agent {label} {' | '.join(tail)} {p.stderr[-200:]}"


def run(r):
    try:
        return fetch_agent(r) if r["kind"] == "agent" else fetch_generator(r)
    except Exception as exc:
        return f"FAIL {r['kind']} {r['name']} {r['id'][:8]}: {exc}"


with ThreadPoolExecutor(6) as pool:
    for line in pool.map(run, todo):
        print(line, flush=True)
