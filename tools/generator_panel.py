"""Run our generator's packs against a local agent with the official challenge scorer.

Starts one harness image the way tools/practice_docker.py does (OpenRouter gpt-oss-20b, the
embedding shim), then runs `challenge-scorer run` from the upstream repo on the generator source
and prints, per case family, how many cases the agent solved (score >= 0.5) and its mean score.
With one agent nothing can be "discriminating" (that needs two owners), so this only shows
which families our own agent finds trivial or impossible.

    python3 tools/generator_panel.py --image ditto-harness:combined-tool4 --seeds 1 --cases 16

Needs OPENROUTER_API_KEY in .env.local. Writes practice/generator/<stamp>/run.json.
"""

import argparse
import collections
import http.server
import json
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
SCORER = HERE / ".cache" / "challenge-scorer"
TEST_HOTKEY = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"


class NullToolsProxy(http.server.BaseHTTPRequestHandler):
    """Forward to the harness, turning `"tools": null` into `[]`.

    The local challenge runner sends memory cases with tools null, and our harness's request
    model requires a list, so without this every case comes back as a malformed request."""

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


def start_proxy(target: str) -> str:
    handler = type("Proxy", (NullToolsProxy,), {"target": target})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


def family(case_id: str) -> str:
    return case_id.rsplit("-", 1)[0]


def summarize(run: dict) -> None:
    """Per family: cases, solved by the agent, mean score; walks whatever case rows the file has."""
    rows = []

    def walk(node):
        if isinstance(node, dict):
            if "case_id" in node and "score" in node:
                rows.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(run.get("input", run))
    by = collections.defaultdict(list)
    for r in rows:
        by[family(r["case_id"])].append(float(r["score"]))
    print(f"{'family':14s} cases solved mean")
    for name, scores in sorted(by.items()):
        solved = sum(s >= 0.5 for s in scores)
        print(f"{name:14s} {len(scores):5d} {solved:6d} {sum(scores) / len(scores):.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="ditto-harness:combined-tool4")
    ap.add_argument("--dir", type=Path, default=HERE / "generator")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1, help="first rehearsal seed")
    ap.add_argument("--cases", type=int, default=16)
    ap.add_argument("--harness-port", type=int, default=8180,
                    help="8080 is left to tools/practice_docker.py, so both can run at once")
    ap.add_argument("--env-file", type=Path, default=HERE / ".env.local")
    ap.add_argument("--summarize", type=Path, help="only print the table for an existing run.json")
    args = ap.parse_args()
    if args.summarize:
        summarize(json.loads(args.summarize.read_text()))
        return 0

    key = pd.load_env_file(args.env_file).get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not key.strip():
        print(f"OPENROUTER_API_KEY missing: put it in {args.env_file}", file=sys.stderr)
        return 2
    if not SCORER.is_file():
        subprocess.run(["go", "build", "-o", str(SCORER), "./cmd/challenge-scorer"], cwd=API_DIR, check=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = HERE / "practice" / "generator" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (embed_port,) = pd.lr.reserve_ports(1)
    harness_url = f"http://127.0.0.1:{args.harness_port}"
    container = f"ditto-generator-{args.harness_port}"
    child_env = dict(os.environ, OPENROUTER_API_KEY=key)
    shim = None
    try:
        shim = subprocess.Popen(
            [sys.executable, str(HERE / "tools" / "embed_shim.py"), "--port", str(embed_port)],
            env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        # the key goes in through the environment, not the command line
        subprocess.run(
            ["docker", "run", "-d", "--rm", "--name", container, "--network", "host",
             "-e", f"PORT={args.harness_port}", "-e", "DITTOBENCH_PROVIDER=openrouter",
             "-e", "DITTOBENCH_MODEL=openai/gpt-oss-20b", "-e", "OPENROUTER_API_KEY",
             "-e", f"OLLAMA_BASE_URL=http://127.0.0.1:{embed_port}",
             "-e", "DITTOBENCH_DB=/tmp/practice.db", args.image],
            env=child_env, check=True, stdout=subprocess.DEVNULL)
        pd.wait_http(f"http://127.0.0.1:{embed_port}/health")
        pd.wait_http(f"{harness_url}/health")
        print(f"{args.image}: {args.seeds} seed(s) x {args.cases} cases", flush=True)
        run_json = out_dir / "run.json"
        subprocess.run(
            [str(SCORER), "run", "-dir", str(args.dir), "-hotkey", TEST_HOTKEY, "-sandbox", "local",
             "-seeds", str(args.seeds), "-seed", str(args.seed), "-cases", str(args.cases),
             "-agent", f"horizon={start_proxy(harness_url)},owner=us", "-out", str(run_json)],
            cwd=API_DIR, check=True)
        summarize(json.loads(run_json.read_text()))
        print(f"saved {out_dir}")
        return 0
    finally:
        logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
        (out_dir / "harness.log").write_text(pd.redact(logs.stdout + logs.stderr))
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        pd.lr.stop_process(shim)


if __name__ == "__main__":
    sys.exit(main())
