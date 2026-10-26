"""Score a Docker-built harness with the official DittoBench scorer (local practice).

The official `ditto practice` only runs Rust starter-kit harnesses (cargo). This runs any
harness image instead, and otherwise uses the official rehearsal code unchanged: same scorer
build, scorer environment, submit body, polling, and summary (imported from the starter kit's
scripts/local-rehearsal.py). Chat goes to OpenRouter gpt-oss-20b, embeddings go through
tools/embed_shim.py to the same pinned model validators use.

    python3 tools/practice_docker.py --image ditto-harness:base --run-size small

Needs OPENROUTER_API_KEY in .env.local (KEY=VALUE lines, never committed).
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
KIT_SCRIPTS = HERE / "repos" / "ditto-subnet" / "miners" / "dittobench-starter-kit" / "scripts"
sys.path.insert(0, str(KIT_SCRIPTS))
_spec = importlib.util.spec_from_file_location("local_rehearsal", KIT_SCRIPTS / "local-rehearsal.py")
lr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lr)

SCORER_BIN = HERE / ".cache" / "dittobench-api"
SUBSET_SCORER_BIN = HERE / ".cache" / "dittobench-api-subset"
LIVE_BENCH = 13  # live contract on 2026-10-22 (/api/v1/public/bench/config); the kit still says 12


def load_env_file(path: Path) -> dict:
    values = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def redact(text: str) -> str:
    for pattern in lr.SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "<redacted>", text)
    return re.sub(r"sk-or-v1-[A-Za-z0-9_-]+", "<redacted>", text)


def wait_http(url: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"{url} did not answer within {timeout:.0f}s")


def ensure_scorer() -> None:
    if SCORER_BIN.is_file():
        return
    SCORER_BIN.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["go", "build", "-o", str(SCORER_BIN), "./cmd/dittobench-api"],
                   cwd=lr.API_DIR, env=lr.sanitized_build_env(), check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="ditto-harness:dev")
    ap.add_argument("--run-size", choices=("small", "medium", "full"), default="small")
    ap.add_argument("--bench-version", type=int, default=LIVE_BENCH)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--concurrency", type=int, default=2, help="scorer case concurrency")
    ap.add_argument("--env-file", type=Path, default=HERE / ".env.local")
    ap.add_argument("--out", type=Path, default=HERE / "practice")
    ap.add_argument("--harness-port", type=int, default=8080,
                    help="port the image listens on; validators use 8080 and some images ignore PORT")
    ap.add_argument("--trace", action="store_true", help="write the practice trace (trace images only) to the run folder")
    ap.add_argument("--env", action="append", default=[], help="extra KEY=VALUE for the harness container, repeatable")
    ap.add_argument("--only-cases", type=Path,
                    help="re-run only these canonical case ids (needs the subset scorer, tools/build_subset_scorer.py)")
    ap.add_argument("--replay-writes", type=Path,
                    help="memory writes from tools/replay_writes.py for the harness to put back after the first seed (with --trace)")
    args = ap.parse_args()
    scorer_bin = SUBSET_SCORER_BIN if args.only_cases else SCORER_BIN
    if args.only_cases and not scorer_bin.is_file():
        print(f"{scorer_bin} missing: run tools/build_subset_scorer.py", file=sys.stderr)
        return 2
    if args.replay_writes and not args.trace:
        print("--replay-writes goes through the trace folder: add --trace", file=sys.stderr)
        return 2

    secrets_env = load_env_file(args.env_file)
    key = secrets_env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not key.strip():
        print(f"OPENROUTER_API_KEY missing: put it in {args.env_file}", file=sys.stderr)
        return 2
    ensure_scorer()
    os.environ["DITTOBENCH_V8_CASE_CONCURRENCY"] = str(args.concurrency)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out / f"{stamp}_{args.image.replace(':', '-').replace('/', '_')}_{args.run_size}{'_rerun' if args.only_cases else ''}"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.only_cases:
        (out_dir / "only_cases.txt").write_text(args.only_cases.read_text())
    if args.replay_writes:
        (out_dir / "replay_writes.jsonl").write_text(args.replay_writes.read_text(encoding="utf-8"), encoding="utf-8")
        args.env.append("HARNESS_REPLAY_WRITES=/trace/replay_writes.jsonl")
    api_port, broker_port, embed_port = lr.reserve_ports(3)
    harness_port = args.harness_port
    harness_url, api_url = f"http://127.0.0.1:{harness_port}", f"http://127.0.0.1:{api_port}"
    container = f"ditto-practice-{harness_port}"
    child_env = dict(os.environ, OPENROUTER_API_KEY=key)

    shim = api = None
    with tempfile.TemporaryDirectory(prefix="ditto-practice-") as raw_tmp:
        tmp = Path(raw_tmp)
        try:
            shim = subprocess.Popen(
                [sys.executable, str(HERE / "tools" / "embed_shim.py"), "--port", str(embed_port)],
                env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # host network: the harness reaches the scorer's tool endpoint and the shim on 127.0.0.1;
            # the key goes in through the environment, not the command line
            subprocess.run(
                ["docker", "run", "-d", "--rm", "--name", container, "--network", "host",
                 "-e", f"PORT={harness_port}", "-e", "DITTOBENCH_PROVIDER=openrouter",
                 "-e", "DITTOBENCH_MODEL=openai/gpt-oss-20b", "-e", "OPENROUTER_API_KEY",
                 "-e", f"OLLAMA_BASE_URL=http://127.0.0.1:{embed_port}",
                 "-e", "DITTOBENCH_DB=/tmp/practice.db",
                 *(["-v", f"{out_dir}:/trace", "-e", "HARNESS_TRACE_DIR=/trace"] if args.trace else []),
                 *[x for env in args.env for x in ("-e", env)],
                 args.image],
                env=child_env, check=True, stdout=subprocess.DEVNULL)
            api_log = (out_dir / "scorer.log").open("wb")
            scorer_env = lr.scorer_environment(tmp, broker_port)
            if args.only_cases:
                scorer_env["DITTOBENCH_ONLY_CASES"] = str((out_dir / "only_cases.txt").resolve())
            api = subprocess.Popen([str(scorer_bin), "-port", str(api_port)], cwd=lr.API_DIR,
                                   env=scorer_env,
                                   stdout=api_log, stderr=subprocess.STDOUT)
            print("waiting for harness, scorer and embedding shim...", flush=True)
            wait_http(f"http://127.0.0.1:{embed_port}/health")
            wait_http(f"{harness_url}/health")
            lr.wait_for_health(api_url, api)
            lr.require_scorer_bench_version(api_url, args.bench_version)
            accepted = lr.request_json(f"{api_url}/v1/submit", method="POST",
                                       payload=lr.submit_body(args.run_size, harness_url,
                                                              args.seed, args.bench_version))
            run_id = accepted["run_id"]
            print(f"bench v{args.bench_version} {args.run_size} run {run_id}", flush=True)
            completed = lr.poll_run(api_url, run_id, timeout=args.timeout)
            print(lr.format_summary(completed))
            lr.write_report(out_dir / "report.json", completed)
            print(f"saved {out_dir}")
            return 0 if completed.get("status") == "done" else 1
        finally:
            logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
            (out_dir / "harness.log").write_text(redact(logs.stdout + logs.stderr))
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
            for proc in (api, shim):
                lr.stop_process(proc)


if __name__ == "__main__":
    sys.exit(main())
