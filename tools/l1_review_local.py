"""Run one L1 source review of a local harness tree with the screener's own reviewer.

    .cache/screener-venv/bin/python tools/l1_review_local.py TREE OUT.json [--key-file F]

Packs TREE (caches left out) into a tarball the way an upload is packed and hands it to the
upstream screener's OpenRouterSourceReviewAgent with the production defaults from its config
(openai/gpt-6-luna, high reasoning effort, 200 steps, 8 MB read budget, 8000 output tokens per
step). The reviewer has read-only file tools; nothing in TREE is executed. The observation (risk
level, categories, findings, notes) is written to OUT.json. This is L1 only: the platform's L2/L3
reviewers and adjudicator are not run. The key file holds the OpenRouter key alone, mode 0600.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "repos" / "ditto-subnet" / "workers" / "screener"))
from ditto_screener.source_review import OpenRouterSourceReviewAgent  # noqa: E402

SKIP_PARTS = {"__pycache__", ".git", ".venv"}


def pack(tree: Path, out: Path) -> str:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted(tree.rglob("*")):
            if path.is_file() and not path.is_symlink() and not SKIP_PARTS & set(path.parts):
                info = tar.gettarinfo(str(path), arcname=path.relative_to(tree).as_posix())
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                with open(path, "rb") as handle:
                    tar.addfile(info, handle)
    out.write_bytes(buffer.getvalue())
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def plain(value):
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)


async def run(args) -> int:
    tarball = args.out.with_suffix(".tar.gz")
    sha = pack(args.tree, tarball)
    print(f"packed {args.tree} -> {tarball} sha256 {sha[:16]}", flush=True)
    agent = OpenRouterSourceReviewAgent(
        api_key_file=str(args.key_file), model=args.model, base_url="https://openrouter.ai/api/v1",
        timeout_seconds=1800, max_steps=200, max_read_bytes=8_000_000, max_completion_tokens=8000,
        reasoning_effort="high")
    steps = {"done": 0}

    def progress(done: int, total: int) -> None:
        if done // 10 != steps["done"] // 10:
            print(f"  review step {done}/{total}", flush=True)
        steps["done"] = done

    observation = await agent.review(str(tarball), artifact_sha256=sha, progress=progress)
    result = plain(observation)
    args.out.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result.get(k) for k in ("risk_level", "categories", "clearance_certified", "reason_code")}, indent=1))
    for finding in result.get("findings") or []:
        print("FINDING", json.dumps(finding)[:700])
    print(f"notes: {len(result.get('notes') or [])}; full observation in {args.out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tree", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--key-file", type=Path, default=HERE / ".cache" / "review_key")
    ap.add_argument("--model", default="openai/gpt-6-luna")
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
