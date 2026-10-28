"""Run the screener's L2/L3 source review on a local tarball, built the way the platform's gate builds it.

    .cache/screener-venv/bin/python tools/l2l3_review_local.py TARBALL L1_OBSERVATION.json OUT.json \
        [--max-cost-usd 25] [--dry-run]

Mirrors workers/screener/ditto_screener/gate.py `_configure_source_reviewer` with the production
defaults of config.py: L2 analyst openai/gpt-6-sol (fallback z-ai/glm-5.2), L3 critic openai/gpt-6-sol
at medium effort, adjudicator z-ai/glm-5.3-flash, the isolated no-network analyzer container
(deploy/l2-analyzer.Dockerfile, built as ditto-screener-l2-analyzer:local), mode enforce and always
escalate (policy v13 escalates every attempt; a low, certified L1 still reaches L2 there).

L1 is not run again: the observation written by tools/l1_review_local.py for the same tarball (same
sha256, production L1 settings) is handed to the layered agent's `resolve_lead`, as the platform does
with its own L1 result. What a local run lacks: the platform's signed scorer runtime lease and any
review-settings revision the operators applied on top of the defaults.

--dry-run checks the tarball, the L1 binding, the analyzer image and the key file, prints the
configuration, and stops before any model call.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent
SCREENER = HERE / "repos" / "ditto-subnet" / "workers" / "screener"
sys.path.insert(0, str(SCREENER))
from ditto_screener.adjudicator import build_adjudicator  # noqa: E402
from ditto_screener.l2_review import (  # noqa: E402
    IsolatedCodingHarness,
    L2AuditJournal,
    LayeredSourceReviewAgent,
    TerraSolSourceReviewAgent,
)
from ditto_screener.policy import SourceReviewObservation  # noqa: E402
from ditto_screener.source_review import OpenRouterSourceReviewAgent  # noqa: E402

IMAGE = "ditto-screener-l2-analyzer:local"
# config.py production defaults (gate.py passes these to the agents)
PRODUCTION = dict(
    l1_model="openai/gpt-6-luna", l1_timeout=1800, l1_steps=200, l1_read=8_000_000, l1_completion=8000, l1_effort="high",
    l2_model="openai/gpt-6-sol", l2_fallbacks=("z-ai/glm-5.2",), l3_model="openai/gpt-6-sol",
    l2_timeout=1800.0, l2_steps=256, l2_input=5_000_000, l2_output=1_000_000, l2_completion=16_000,
    l2_cost=25.0, analyst_effort="model_default", critic_effort="medium",
    adjudicator_mode="enforce", adjudicator_model="z-ai/glm-5.3-flash", adjudicator_steps=128, adjudicator_timeout=600.0,
    concern_hold=3, clear_min_notes=3,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def l1_observation(path: Path) -> SourceReviewObservation:
    raw = json.loads(path.read_text())
    fields = {f.name for f in dataclasses.fields(SourceReviewObservation)}
    value = {k: v for k, v in raw.items() if k in fields}
    value["categories"] = tuple(value.get("categories") or ())
    if "notes" in value:
        value["notes"] = tuple(value["notes"])
    return SourceReviewObservation(**value)


def build(args, cost_cap: float) -> LayeredSourceReviewAgent:
    p = PRODUCTION
    l1 = OpenRouterSourceReviewAgent(
        api_key_file=str(args.key_file), model=p["l1_model"], base_url="https://openrouter.ai/api/v1",
        timeout_seconds=p["l1_timeout"], max_steps=p["l1_steps"], max_read_bytes=p["l1_read"],
        max_completion_tokens=p["l1_completion"], reasoning_effort=p["l1_effort"],
        concern_hold_count=p["concern_hold"], clear_min_notes=p["clear_min_notes"])
    work = args.out.parent / "l2_work"
    work.mkdir(parents=True, exist_ok=True)
    l2 = TerraSolSourceReviewAgent(
        api_key_file=str(args.key_file), base_url="https://openrouter.ai/api/v1",
        harness=IsolatedCodingHarness(docker_bin="docker", image=IMAGE),
        workspace_root=str(work / "workspace"), cache_dir=str(work / "cache"),
        audit_journal=L2AuditJournal(str(work / "audit.jsonl"), retention_days=30),
        timeout_seconds=p["l2_timeout"], max_steps=p["l2_steps"], max_input_tokens=p["l2_input"],
        max_output_tokens=p["l2_output"], max_completion_tokens=p["l2_completion"], max_cost_usd=cost_cap,
        analyst_reasoning_effort=p["analyst_effort"], critic_reasoning_effort=p["critic_effort"],
        cache_ttl_seconds=0.0, model=p["l2_model"], fallback_models=p["l2_fallbacks"], l3_enabled=True,
        critic_model=p["l3_model"], retry_provider_body_fault_once=True, local_address="0.0.0.0")
    config = SimpleNamespace(
        adjudicator_mode=p["adjudicator_mode"], source_review_api_key_file=str(args.key_file),
        source_review_base_url="https://openrouter.ai/api/v1", review_inference_provider="openrouter",
        adjudicator_model=p["adjudicator_model"], adjudicator_timeout_seconds=p["adjudicator_timeout"],
        adjudicator_max_steps=p["adjudicator_steps"], adjudicator_max_completion_tokens=None,
        l2_max_completion_tokens=p["l2_completion"])
    return LayeredSourceReviewAgent(
        l1=l1, l2=l2, mode="enforce", concern_hold_count=p["concern_hold"], clear_min_notes=p["clear_min_notes"],
        adjudicator=build_adjudicator(config), adjudicator_reserve_seconds=p["adjudicator_timeout"], always_escalate=True)


def checks(args) -> tuple[str, SourceReviewObservation]:
    sha = sha256(args.tarball)
    observation = l1_observation(args.l1)
    bound = (json.loads(args.l1.read_text()).get("finding") or {}).get("artifact_sha256")
    print(f"tarball {args.tarball} sha256 {sha[:16]}; L1 bound to {str(bound)[:16]}; L1 risk {observation.risk_level}, certified {observation.clearance_certified}")
    if bound and bound != sha:
        raise SystemExit("the L1 observation belongs to another tarball; review that tarball, or rerun L1 on this one")
    if not args.key_file.is_file():
        raise SystemExit(f"no key file at {args.key_file}")
    image = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    print(f"analyzer image {IMAGE}: {'present' if image.returncode == 0 else 'MISSING (docker build -f workers/screener/deploy/l2-analyzer.Dockerfile -t ' + IMAGE + ' workers/screener)'}")
    if image.returncode != 0:
        raise SystemExit(1)
    return sha, observation


async def run(args) -> int:
    sha, observation = checks(args)
    agent = build(args, args.max_cost_usd)
    print(f"configuration: L2 {PRODUCTION['l2_model']} (fallback {', '.join(PRODUCTION['l2_fallbacks'])}), L3 {PRODUCTION['l3_model']}, "
          f"adjudicator {PRODUCTION['adjudicator_model']}, cost cap ${args.max_cost_usd}, always escalate, mode enforce")
    if args.dry_run:
        print("dry run: stopping before any model call")
        return 0
    started = time.monotonic()
    deadline = asyncio.get_running_loop().time() + PRODUCTION["l2_timeout"] + PRODUCTION["adjudicator_timeout"]
    result = await agent.resolve_lead(str(args.tarball), artifact_sha256=sha, attempt_id=uuid.uuid4(),
                                      l1_observation=observation, deadline=deadline, policy_version=13)
    out = plain(result)
    args.out.write_text(json.dumps(out, indent=1))
    finding = out.get("finding") or {}
    print(json.dumps({k: out.get(k) for k in ("ok", "risk_level", "categories", "clearance_certified", "violation_certified", "error_code", "failure_subcode")}, indent=1))
    for d in ((finding.get("invariant_assessment") or {}).get("decisions") or []):
        print(f"  {d.get('invariant'):28s} {d.get('disposition'):7s} {d.get('pass_clause') or ''} | {str(d.get('summary'))[:200]}")
    print(f"seconds {int(time.monotonic() - started)}; audit (tokens, cost) in {args.out.parent / 'l2_work' / 'audit.jsonl'}; full observation in {args.out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tarball", type=Path)
    ap.add_argument("l1", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--key-file", type=Path, default=HERE / ".cache" / "review_key")
    ap.add_argument("--max-cost-usd", type=float, default=PRODUCTION["l2_cost"])
    ap.add_argument("--dry-run", action="store_true")
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
