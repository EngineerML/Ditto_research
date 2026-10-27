"""Free end-to-end check of a harness image: real /seed and /run requests, mock model.

Seeds a generated dataset's world and memory records into the image, then sends a few
tool and memory questions with HARNESS_MOCK_MODEL=1, so no chat model is paid for.
Embeddings go through tools/embed_shim.py (about $0.0001). Prints the lane each case took
and the packet sizes from the harness log.

    .venv/bin/python tools/mock_smoke.py --image ditto-harness:dev --cases 12
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from lab import data  # noqa: E402
from lab.embed import api_key  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(url: str, body: dict, timeout: float = 600) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def wait(url: str, seconds: float = 60) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            urllib.request.urlopen(url, timeout=3).close()
            return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"{url} did not answer")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="ditto-harness:dev")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--cases", type=int, default=12)
    ap.add_argument("--trace-dir", default="", help="host folder for the practice trace (trace images only)")
    args = ap.parse_args()
    cases = data.load(args.seed, 0, "small")
    harness_port, embed_port = free_port(), free_port()
    shim = subprocess.Popen([sys.executable, str(HERE / "tools" / "embed_shim.py"), "--port", str(embed_port)],
                            env=dict(os.environ, OPENROUTER_API_KEY=api_key()), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    name = f"ditto-smoke-{harness_port}"
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "--network", "host", "-e", f"PORT={harness_port}",
                        "-e", "HARNESS_MOCK_MODEL=1", "-e", f"OLLAMA_BASE_URL=http://127.0.0.1:{embed_port}",
                        "-e", "DITTOBENCH_DB=/tmp/smoke.db",
                        *(["-v", f"{args.trace_dir}:/trace", "-e", "HARNESS_TRACE_DIR=/trace"] if args.trace_dir else []),
                        args.image, "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(harness_port)], check=True, stdout=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{harness_port}"
        wait(f"{base}/health")
        wait(f"http://127.0.0.1:{embed_port}/health")
        stores: dict[str, tuple] = {}
        for case in cases:
            stores.setdefault(case.user, case.store)
            if len(case.store) > len(stores[case.user]):
                stores[case.user] = case.store
        for user, store in stores.items():
            pairs = [{"pair_id": r.pair_id, "session_id": r.session_id, "timestamp": r.timestamp, "prompt": r.prompt,
                      "response": r.response} for r in store]
            started = time.monotonic()
            print(f"seed {user}: {len(pairs)} records ->", post(f"{base}/seed", {"user_id": user, "pairs": pairs, "subjects": [], "links": []}),
                  f"{time.monotonic() - started:.1f}s")
        random.Random(1).shuffle(cases)
        picked = [c for c in cases if c.phase == "tool"][: args.cases // 3] + [c for c in cases if c.phase == "memory"][: args.cases - args.cases // 3]
        for case in picked:
            body = {"case_id": case.key.rsplit("/", 1)[-1], "user_id": case.user, "user_input": case.text, "system_prompt": "",
                    "tools": [{"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters")} for t in case.catalog]}
            try:
                reply = post(f"{base}/run", body)
            except urllib.error.HTTPError:
                print("\n".join(subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr.splitlines()[-25:]))
                raise
            print(f"[{case.lane:7s}] {case.phase}:{case.kind[:30]:30s} -> answer={reply.get('answer')!r} calls={len(reply.get('tool_calls') or [])}")
        logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr
        for line in logs.splitlines():
            if "lane=" in line and "case=" in line and "user=" in line:
                lane = re.search(r"lane=(\S+)", line)
                packet = re.search(r"packet records=\d+ chars=\d+ widened=\d+", line)
                print("  log:", lane.group(1) if lane else "?", packet.group(0) if packet else "")
            elif "Traceback" in line or "ERROR" in line:
                print("  log!", line[:200])
        return 0
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        shim.terminate()


if __name__ == "__main__":
    sys.exit(main())
