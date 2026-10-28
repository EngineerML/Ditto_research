"""Run one L1 source review of a local harness tree with the screener's own reviewer.

    .cache/screener-venv/bin/python tools/l1_review_local.py TREE_OR_TARBALL OUT.json [--key-file F] \
        [--lineage PACKET.json] [--dry-run]

Packs TREE (caches left out) into a tarball the way an upload is packed, or takes an upload tarball
as it is (copied next to OUT.json, so the L2/L3 tool finds it), and hands it to the
upstream screener's OpenRouterSourceReviewAgent with the production defaults from its config
(openai/gpt-6-luna, high reasoning effort, 200 steps, 8 MB read budget, 8000 output tokens per
step). The reviewer has read-only file tools; nothing in TREE is executed. The observation (risk
level, categories, findings, notes) is written to OUT.json. This is L1 only: the platform's L2/L3
reviewers and adjudicator are not run. The key file holds the OpenRouter key alone, mode 0600.

--lineage hands the reviewer a resubmission's lineage packet (tools/lineage_packet_local.py), as the
platform does since diff-scoped screening: the diff from the prior version, the rulings and the prior
findings. The packet must be built for this exact tarball.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "repos" / "ditto-subnet" / "workers" / "screener"))
from ditto_screener.source_review import OpenRouterSourceReviewAgent  # noqa: E402
from ditto_screening_protocol import ReviewLineagePacket  # noqa: E402

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


def lineage(path: Path | None, sha: str) -> ReviewLineagePacket | None:
    if path is None:
        return None
    packet = ReviewLineagePacket.model_validate_json(path.read_text())
    if packet.artifact_sha256 != sha:
        raise SystemExit(f"the lineage packet {path} was built for another tarball ({packet.artifact_sha256[:16]})")
    print(f"lineage packet {packet.packet_sha256[:16]}: parent v{packet.parent.version}, scope {packet.scope.value}, "
          f"{packet.changed_file_count} files changed, {len(packet.rulings)} rulings, {len(packet.findings)} findings", flush=True)
    return packet


async def run(args) -> int:
    tarball = args.out.with_suffix(".tar.gz")
    if args.tree.is_file():
        shutil.copyfile(args.tree, tarball)
        sha = hashlib.sha256(tarball.read_bytes()).hexdigest()
        print(f"reviewing {args.tree} as uploaded (copied to {tarball}) sha256 {sha[:16]}", flush=True)
    else:
        sha = pack(args.tree, tarball)
        print(f"packed {args.tree} -> {tarball} sha256 {sha[:16]}", flush=True)
    packet = lineage(args.lineage, sha)
    if args.dry_run:
        print("dry run: stopping before any model call")
        return 0
    agent = OpenRouterSourceReviewAgent(
        api_key_file=str(args.key_file), model=args.model, base_url="https://openrouter.ai/api/v1",
        timeout_seconds=1800, max_steps=200, max_read_bytes=8_000_000, max_completion_tokens=8000,
        reasoning_effort="high")
    steps = {"done": 0}

    def progress(done: int, total: int) -> None:
        if done // 10 != steps["done"] // 10:
            print(f"  review step {done}/{total}", flush=True)
        steps["done"] = done

    observation = await agent.review(str(tarball), artifact_sha256=sha, progress=progress, review_lineage=packet)
    result = plain(observation)
    result["lineage_packet_sha256"] = packet.packet_sha256 if packet else None
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
    ap.add_argument("--lineage", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
