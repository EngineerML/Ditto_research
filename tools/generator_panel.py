"""Run our generator's packs against a local panel of agent images with the official challenge scorer.

Packs are rehearsed as a live round would request them (`--round-bench`, 15 by default, so they are graded
at the policy they declare), then each pack runs against every agent in fresh containers, so no memory
carries over between packs. Per case family (the case id without its round number) it prints, for each
agent, how many cases it solved (score >= 0.5) and its mean, plus the scorer's discriminating / trivial /
unsolved split over the whole panel.

    python3 tools/generator_panel.py --agent drp=drp23v15 --agent dan0l=v30-released --seeds 1 --cases 80
    python3 tools/generator_panel.py --mock --agent drp=drp23v15 --agent dan0l=v30-released --seeds 3

--mock is free: a fake model and fake embeddings stand in for OpenRouter, so nothing is graded, but every
traced image records per case the lane it chose, the reading path and the records it put in front of the
model. The summary then shows, per family and agent, the lanes, the paths and how often the case's
evidence pairs reached the packet.

The real run needs OPENROUTER_API_KEY in .env.local and costs about $0.003 per case per agent.
Writes practice/generator/<stamp>/ (packs, run-*.json, traces, harness logs).
"""

import argparse
import collections
import glob
import hashlib
import http.server
import json
import math
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practice_docker as pd  # noqa: E402

HERE = pd.HERE
API_DIR = HERE / "repos" / "ditto-subnet" / "services" / "dittobench-api"
DATAGEN_DIR = HERE / "repos" / "ditto-subnet" / "research" / "dittobench-datagen"
SCORER = HERE / ".cache" / "challenge-scorer"
TEST_HOTKEY = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"


def check_key(key: str) -> str:
    """Ask OpenRouter about the key before anything starts; return the problem, or "" when it is usable.

    The key endpoint is free. It catches an expired or revoked key and a shell without the proxy, which
    otherwise only show up as empty answers after the agents have spent minutes seeding."""
    req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp).get("data") or {}
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code} {exc.read()[:200].decode(errors='replace')}"
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return f"{type(exc).__name__}: {exc} (is the proxy loaded? source /etc/profile.d/zz-proxy.sh)"
    left = data.get("limit_remaining")
    print(f"OpenRouter key ok, limit remaining: {'none set' if left is None else f'${left:.2f}'}", flush=True)
    return ""


class NullToolsProxy(http.server.BaseHTTPRequestHandler):
    """Forward to the harness, turning `"tools": null` into `[]`.

    The local challenge runner sends memory cases with tools null, and some harnesses' request models
    require a list, so without this every case comes back as a malformed request."""

    target = ""

    def forward(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        if body:
            try:
                data = json.loads(body)
                if isinstance(data, dict) and "tools" in data and data["tools"] is None:
                    data["tools"] = []
                    body = json.dumps(data).encode()
            except ValueError:
                pass
        req = urllib.request.Request(self.target + self.path, data=body, method=self.command,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        try:
            with urllib.request.urlopen(req, timeout=900) as resp:
                status, payload = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, payload = exc.code, exc.read()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_DELETE = forward

    def log_message(self, *args) -> None:
        pass


class FakeModel(http.server.BaseHTTPRequestHandler):
    """A stand-in for OpenRouter chat and the Ollama-style embedding gateway, for --mock runs.

    Chat always answers one fixed line with no tool call. Embeddings are hashed bags of words, so similar
    texts still land near each other and retrieval behaves roughly as it would."""

    def reply(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.reply({"status": "ok"})

    def do_POST(self) -> None:
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path.endswith("/chat/completions"):
            self.reply({"id": "mock", "object": "chat.completion", "model": req.get("model", "mock"),
                        "choices": [{"index": 0, "finish_reason": "stop",
                                     "message": {"role": "assistant", "content": "ANSWER: unknown"}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
            return
        texts = req.get("input", req.get("prompt", ""))
        single = isinstance(texts, str)
        vectors = [embed(t) for t in ([texts] if single else texts)]
        self.reply({"embedding": vectors[0]} if self.path == "/api/embeddings" else {"embeddings": vectors})

    def log_message(self, *args) -> None:
        pass


def embed(text: str, dims: int = 768) -> list[float]:
    v = [0.0] * dims
    for word in text.lower().split():
        v[int(hashlib.sha256(word.strip(".,;:!?\"'()").encode()).hexdigest(), 16) % dims] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def serve(handler, target: str = "") -> str:
    if target:
        handler = type("Proxy", (handler,), {"target": target})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


def family(case_id: str) -> str:
    return case_id.rsplit("-", 1)[0]


def rehearse(args, out: Path) -> list[Path]:
    packs = out / "packs"
    packs.mkdir(parents=True, exist_ok=True)
    subprocess.run(["go", "run", "./cmd/challenge", "rehearse", "-dir", str(args.dir), "-hotkey", TEST_HOTKEY,
                    "-seeds", str(args.seeds), "-seed", str(args.seed), "-cases", str(args.cases),
                    "-round-bench", str(args.round_bench), "-out-dir", str(packs)], cwd=DATAGEN_DIR, check=True)
    paths = sorted(packs.glob("*.json"))
    if args.only:
        # Keep the whole haystack, so the agents read exactly what a round would seed, and ask only the
        # cases under test: a paid check of one family costs a fraction of the full pack.
        prefixes = tuple(x.strip() for x in args.only.split(",") if x.strip())
        for path in paths:
            pack = json.loads(path.read_text())
            keep = [c for c in pack["cases"] if c["id"].startswith(prefixes)]
            # A pack holds at least 8 cases; top a small selection up with the pack's other cases.
            keep += [c for c in pack["cases"] if not c["id"].startswith(prefixes)][:max(0, 8 - len(keep))]
            pack["cases"] = keep
            path.write_text(json.dumps(pack))
            print(f"{path.stem}: asking {len(pack['cases'])} cases matching {', '.join(prefixes)}", flush=True)
    return paths


def start_agents(args, out: Path, tag: str, env: dict, model_url: str, embed_url: str) -> list[tuple[str, str, str]]:
    """Start one container per agent; returns (agent id, proxy url, container name)."""
    started = []
    for k, (agent, image) in enumerate(args.agent):
        port = args.harness_port + k
        container = f"ditto-generator-{port}"
        trace = out / "trace" / tag / agent
        trace.mkdir(parents=True, exist_ok=True)
        trace.chmod(0o777)  # the harness may run as an unprivileged user
        cmd = ["docker", "run", "-d", "--rm", "--name", container, "--network", "host",
               "-e", f"PORT={port}", "-e", "DITTOBENCH_PROVIDER=openrouter",
               "-e", "DITTOBENCH_MODEL=openai/gpt-oss-20b", "-e", "OPENROUTER_API_KEY",
               "-e", f"OLLAMA_BASE_URL={embed_url}", "-e", "DITTOBENCH_DB=/tmp/practice.db",
               "-v", f"{trace}:/trace", "-e", "HARNESS_TRACE_DIR=/trace"]
        if model_url:
            cmd += ["-e", f"OPENROUTER_BASE_URL={model_url}/v1"]
        # The images' own command binds 8080 whatever PORT says, so give each its port explicitly.
        cmd += [f"ditto-harness:{image}", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port),
                "--workers", "1", "--log-level", "info"]
        subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL)
        started.append((agent, f"http://127.0.0.1:{port}", container))
    try:
        for _, url, _ in started:
            pd.wait_http(f"{url}/health")
    except RuntimeError:
        stop_agents(out, tag, started)
        raise
    return [(agent, serve(NullToolsProxy, url), container) for agent, url, container in started]


def stop_agents(out: Path, tag: str, started) -> None:
    for agent, _, container in started:
        logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
        (out / "trace" / tag / agent / "harness.log").write_text(pd.redact(logs.stdout + logs.stderr))
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)


def summarize(out: Path) -> None:
    """Per family: each agent's solved/n and mean, and the panel's discriminating/trivial/unsolved split."""
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    status = collections.defaultdict(collections.Counter)
    credit = collections.defaultdict(float)
    agents = []
    for run in sorted(out.glob("run-*.json")):
        d = json.loads(run.read_text())
        for seed in d["input"]["seeds"]:
            for slot in seed["panel"]:
                if slot["agent_id"] not in agents:
                    agents.append(slot["agent_id"])
                for r in slot["results"]:
                    per[family(r["case_id"])][slot["agent_id"]].append(float(r["score"]))
        for seed in d["score"]["seeds"]:
            for c in seed["cases"]:
                status[family(c["case_id"])][c["status"]] += 1
                credit[family(c["case_id"])] += float(c.get("credit") or 0)
    if not per:
        return
    print(f"{'family':40s} " + " ".join(f"{a[:12]:>14s}" for a in agents) + "   disc triv unsol  credit/case")
    for name in sorted(per):
        cells = []
        for a in agents:
            s = per[name][a]
            cells.append(f"{sum(x >= 0.5 for x in s):3d}/{len(s):<3d} {sum(s) / len(s):.2f}" if s else " " * 14)
        st, n = status[name], sum(status[name].values())
        print(f"{name:40s} " + " ".join(f"{c:>14s}" for c in cells)
              + f"   {st['discriminating']:4d} {st['trivial']:4d} {st['unsolved']:5d}  {credit[name] / max(n, 1):.2f}")


def summarize_traces(out: Path, packs: list[Path]) -> None:
    """--mock: per family and agent, the lanes, reading paths and how often the evidence reached the packet."""
    # The scorer renames every pair before seeding, so evidence is matched by the start of its prompt,
    # which the trace keeps for each packet record.
    cases, prompt = {}, {}
    for pack in packs:
        p = json.loads(pack.read_text())
        for wave in p["memory_waves"]:
            for pair in wave["pairs"]:
                prompt[pair["pair_id"]] = pair["prompt"][:120]
        for c in sorted(p["cases"], key=lambda c: c.get("run_after_wave", 0)):
            cases.setdefault((pack.stem, c["question"].strip()), []).append(c)
    rows = collections.defaultdict(lambda: collections.defaultdict(lambda: {"lane": collections.Counter(),
                                                                          "path": collections.Counter(),
                                                                          "hit": [], "n": 0}))
    for trace in glob.glob(str(out / "trace" / "*" / "*" / "trace.jsonl")):
        tag, agent = Path(trace).parent.parent.name, Path(trace).parent.name
        stem = tag.rsplit("-r", 1)[0]
        asked = collections.Counter()
        for line in open(trace):
            t = json.loads(line)
            # A question asked again after a later wave is a different case; the scorer finishes a wave's
            # cases before seeding the next, so repeats appear in the trace in wave order.
            key = (stem, str(t.get("user_input", "")).strip())
            same = cases.get(key) or []
            c = same[min(asked[key], len(same) - 1)] if same else None
            asked[key] += 1
            if c is None:
                continue
            r = rows[family(c["id"])][agent]
            r["n"] += 1
            r["lane"][str(t.get("lane", "?")).split(":")[0] + ":" + str(t.get("lane", "?")).split(":")[-1]] += 1
            r["path"][str(t.get("path") or "-")] += 1
            packet = t.get("packet") or []
            shown = {p[1][:120] for p in packet if isinstance(p, list) and len(p) > 1}
            ev = c["evidence_pair_ids"]
            r["hit"].append(sum(prompt[e] in shown for e in ev) / len(ev))
    for name in sorted(rows):
        print(name)
        for agent, r in sorted(rows[name].items()):
            lanes = ", ".join(f"{k} {v}" for k, v in r["lane"].most_common(2))
            paths = ", ".join(f"{k} {v}" for k, v in r["path"].most_common(2))
            hit = sum(r["hit"]) / len(r["hit"]) if r["hit"] else 0
            print(f"    {agent:10s} n={r['n']:<3d} evidence in packet {hit:4.0%}   lanes: {lanes}   paths: {paths}")
    # The families the agents take apart before any model reads them: different lanes or paths, or the
    # evidence reaching one packet and not the other. These are the line splitters.
    print("\nwhere the agents differ before the model:")
    for name in sorted(rows):
        by = rows[name]
        lanes = {a: r["lane"] for a, r in by.items()}
        hits = {a: sum(r["hit"]) / len(r["hit"]) for a, r in by.items() if r["hit"]}
        if len({tuple(sorted(c.items())) for c in lanes.values()}) > 1 or (hits and max(hits.values()) - min(hits.values()) > 0.05):
            print(f"    {name:40s} " + "   ".join(f"{a}: {dict(lanes[a])} {hits.get(a, 0):.0%}" for a in sorted(by)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--agent", action="append", default=[], type=lambda s: tuple(s.split("=", 1)),
                    help="id=image-tag (ditto-harness:<tag>); repeat for each panel agent")
    ap.add_argument("--mock", action="store_true", help="free routing bench: fake model and embeddings, traces only")
    ap.add_argument("--dir", type=Path, default=HERE / "generator")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1, help="first rehearsal seed")
    ap.add_argument("--cases", type=int, default=80)
    ap.add_argument("--repeats", type=int, default=1, help="runs of each pack, to see sampling noise")
    ap.add_argument("--round-bench", type=int, default=15)
    ap.add_argument("--only", help="ask only cases whose id starts with one of these comma-separated prefixes")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--harness-port", type=int, default=8180,
                    help="first harness port; 8080 is left to tools/practice_docker.py")
    ap.add_argument("--env-file", type=Path, default=HERE / ".env.local")
    ap.add_argument("--summarize", type=Path, help="only print the tables for an existing run folder")
    args = ap.parse_args()
    if args.summarize:
        if not args.summarize.name.endswith("-mock"):
            summarize(args.summarize)
        summarize_traces(args.summarize, sorted((args.summarize / "packs").glob("*.json")))
        return 0
    if not args.agent:
        ap.error("give at least one --agent id=image")

    key = "mock"
    if not args.mock:
        key = pd.load_env_file(args.env_file).get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
        if not key.strip():
            print(f"OPENROUTER_API_KEY missing: put it in {args.env_file}", file=sys.stderr)
            return 2
        problem = check_key(key.strip())
        if problem:
            print(f"OpenRouter check failed, nothing started: {problem}", file=sys.stderr)
            return 2
    if not SCORER.is_file():
        subprocess.run(["go", "build", "-o", str(SCORER), "./cmd/challenge-scorer"], cwd=API_DIR, check=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = HERE / "practice" / "generator" / (stamp + ("-mock" if args.mock else ""))
    out.mkdir(parents=True, exist_ok=True)
    packs = rehearse(args, out)
    child_env = dict(os.environ, OPENROUTER_API_KEY=key)
    shim = None
    if args.mock:
        model_url = embed_url = serve(FakeModel)
    else:
        model_url = ""
        (embed_port,) = pd.lr.reserve_ports(1)
        embed_url = f"http://127.0.0.1:{embed_port}"
        shim = subprocess.Popen(
            [sys.executable, str(HERE / "tools" / "embed_shim.py"), "--port", str(embed_port)],
            env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        pd.wait_http(f"{embed_url}/health")
    try:
        for pack in packs:
            for rep in range(args.repeats):
                tag = f"{pack.stem}-r{rep}"
                started = start_agents(args, out, tag, child_env, model_url, embed_url)
                try:
                    print(f"{tag}: {len(started)} agents", flush=True)
                    cmd = [str(SCORER), "run", "-pack", str(pack), "-concurrency", str(args.concurrency),
                           "-out", str(out / f"run-{tag}.json")]
                    for agent, url, _ in started:
                        cmd += ["-agent", f"{agent}={url},owner={agent}"]
                    subprocess.run(cmd, cwd=API_DIR, check=True)
                finally:
                    stop_agents(out, tag, started)
        if not args.mock:
            summarize(out)
        summarize_traces(out, packs)
        print(f"saved {out}")
        return 0
    finally:
        if shim:
            pd.lr.stop_process(shim)


if __name__ == "__main__":
    sys.exit(main())
