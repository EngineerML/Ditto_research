"""Build, locally, the review lineage packet the platform binds to a resubmission's screening attempt.

    .cache/screener-venv/bin/python tools/lineage_packet_local.py CANDIDATE.tgz OUT.json \
        --history live/2026-10-28/lineage --version 1=practice/submission.tgz \
        --version 2=practice/submission_v2.tgz --version 3=practice/submission_v3.tgz

The packet is assembled by the platform's own code (apps/platform/ditto/api_server/review_lineage.py:
the diff, the full-review reasons, the finding text and the sealing), loaded with its database and
storage imports stubbed out; only the rows it would read from the database are rebuilt here, from the
public pipeline and summary of each earlier version (practice/gates/fetch_lineage.sh writes them as
v<N>.json and v<N>_summary.json):

- parent: the highest --version (the same hotkey's prior version, the classic reference); history:
  every --version, newest first;
- rulings: every quarantine resolution on those versions (court "quarantine"), and a resolved dispute
  when the pipeline shows one; ATH actions are not public and none exist for these agents;
- findings: the parent's automated review outcomes, one per screening attempt that left a finding or
  notes: its status, reason, the reviewer revision, and the finding summary, cited locations and
  review notes in the platform's own `_finding_text` layout.

What differs from the platform: the reviewer field holds the public reviewer revision rather than the
model name, a platform event per review stage may be folded into one per attempt here, and the
candidate's agent and attempt ids are local placeholders. The digest is therefore not the platform's,
but the text the reviewers read is the same in substance. Nothing here calls a model.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
import sys
import types
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PLATFORM = HERE / "repos" / "ditto-subnet" / "apps" / "platform"
SCREENER = HERE / "repos" / "ditto-subnet" / "workers" / "screener"
sys.path.insert(0, str(SCREENER))
from ditto_screener.review_lineage_prompt import lineage_l1_text  # noqa: E402


class _Stub(types.ModuleType):
    """A module whose every name is a placeholder class: enough for `from X import Y` of names the
    packet assembly never uses (the ORM, the database session, object storage)."""

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return type(name, (), {})


def platform_lineage():
    for name, path in (("ditto", "ditto"), ("ditto.api_server", "ditto/api_server"), ("ditto.db", "ditto/db"), ("ditto.db.queries", "ditto/db/queries")):
        package = types.ModuleType(name)
        package.__path__ = [str(PLATFORM / path)]
        sys.modules[name] = package
    for name in ("sqlalchemy", "sqlalchemy.ext", "sqlalchemy.ext.asyncio", "ditto.api_server.storage", "ditto.db.models"):
        sys.modules[name] = _Stub(name)
    queries = _Stub("ditto.db.queries.review_lineage")
    queries.REFERENCE_SAME_OWNER_VERSION = "same_owner_version"
    sys.modules[queries.__name__] = queries
    return importlib.import_module("ditto.api_server.review_lineage")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(history: Path, version: int) -> tuple[dict, dict]:
    pipeline = json.loads((history / f"v{version}.json").read_text())
    summary = json.loads((history / f"v{version}_summary.json").read_text())
    if pipeline["agent_id"] != summary["agent_id"] or summary["version"] != version:
        raise SystemExit(f"v{version}: pipeline and summary disagree on the agent or its version")
    return pipeline, summary


def history_row(pipeline: dict, summary: dict, artifact_sha256: str) -> dict:
    policies = [a["policy_version"] for a in pipeline.get("screening_attempts") or [] if a.get("policy_version")]
    return {"agent_id": summary["agent_id"], "version": summary["version"], "artifact_sha256": artifact_sha256,
            "status": summary["status"], "screening_policy_version": policies[0] if policies else None,
            "submitted_at": summary["submitted_at"]}


def rulings(mod, versions: list[tuple[dict, dict]]) -> list[dict]:
    rows = []
    for pipeline, summary in versions:
        for attempt in pipeline.get("screening_attempts") or []:
            if attempt.get("quarantine_resolution") and attempt.get("quarantine_resolved_at"):
                rows.append({"agent_id": summary["agent_id"], "version": summary["version"], "court": "quarantine",
                             "resolution": attempt["quarantine_resolution"], "reason": mod._clip(attempt.get("quarantine_resolution_reason")),
                             "evidence_references": [], "policy_version": attempt.get("policy_version"),
                             "decided_at": attempt["quarantine_resolved_at"]})
        dispute = pipeline.get("dispute") or {}
        if dispute.get("resolution") and dispute.get("resolved_at"):
            rows.append({"agent_id": summary["agent_id"], "version": summary["version"], "court": "dispute",
                         "resolution": dispute["resolution"],
                         "reason": mod._clip(f"miner: {dispute.get('message')}\noperator: {dispute.get('resolution_reason')}"),
                         "evidence_references": [], "policy_version": None, "decided_at": dispute["resolved_at"]})
    rows.sort(key=lambda row: row["decided_at"], reverse=True)
    return rows[: mod.MAX_LINEAGE_RULINGS]


def findings(mod, pipeline: dict, summary: dict) -> list[dict]:
    rows = []
    for attempt in pipeline.get("screening_attempts") or []:
        finding = attempt.get("review_finding") or {}
        notes = attempt.get("review_notes") or []
        if not finding and not notes:
            continue
        evidence = {"finding": {**finding, "evidence": finding.get("locations") or []} if finding else {}, "review_notes": notes}
        codes = [e.get("code") for e in attempt.get("review_evidence") or [] if e.get("module") != "stable-core"]
        rows.append({"agent_id": summary["agent_id"], "version": summary["version"], "attempt_id": attempt["attempt_id"],
                     "policy_version": attempt.get("policy_version"), "reviewer": finding.get("reviewer_revision"),
                     "outcome": attempt["status"], "reason_code": codes[0] if codes else None,
                     "reason": mod._clip(attempt.get("reason")), "finding": mod._finding_text(evidence),
                     "recorded_at": attempt.get("finished_at") or attempt["started_at"]})
    rows.sort(key=lambda row: row["recorded_at"], reverse=True)
    return rows[: mod.MAX_LINEAGE_FINDINGS]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidate", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--history", type=Path, required=True)
    ap.add_argument("--version", action="append", required=True, help="N=TARBALL of an earlier version, its upload")
    ap.add_argument("--policy-version", type=int, default=13)
    args = ap.parse_args()
    mod = platform_lineage()

    tarballs = {int(n): Path(p) for n, p in (v.split("=", 1) for v in args.version)}
    versions = []
    for n in sorted(tarballs, reverse=True):
        pipeline, summary = load(args.history, n)
        versions.append((pipeline, summary, sha256(tarballs[n])))
    candidate_sha = sha256(args.candidate)
    candidate_id = uuid.uuid5(uuid.NAMESPACE_URL, f"local-candidate:{candidate_sha}")
    archives = {uuid.UUID(s["agent_id"]): (tarballs[s["version"]], sha) for _, s, sha in versions}
    archives[candidate_id] = (args.candidate, candidate_sha)

    async def open_local(ref, storage):
        path, expected = archives[uuid.UUID(str(ref.agent_id))]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f"{path} does not match its digest")
        return mod.TarSourceInspector(data)

    mod._open = open_local
    parent_pipeline, parent_summary, parent_sha = versions[0]
    history = [history_row(p, s, sha) for p, s, sha in versions]
    context = mod.ReviewLineageContext(
        agent_id=candidate_id, attempt_id=uuid.uuid5(candidate_id, "local-attempt"), artifact_sha256=candidate_sha,
        policy_version=args.policy_version, candidate=mod._ArtifactRef(candidate_id, candidate_sha),
        parent=mod._ArtifactRef(uuid.UUID(parent_summary["agent_id"]), parent_sha), parent_row=history[0], history=history,
        rulings=rulings(mod, [(p, s) for p, s, _ in versions]), findings=findings(mod, parent_pipeline, parent_summary))
    packet = asyncio.run(mod.assemble_review_lineage_packet(context, None))
    args.out.write_text(packet.model_dump_json(indent=1))

    print(f"candidate {args.candidate} sha256 {candidate_sha[:16]}; parent v{parent_summary['version']} {parent_summary['agent_id'][:8]} sha256 {parent_sha[:16]}")
    print(f"scope {packet.scope.value}{' (' + ', '.join(r.value for r in packet.full_review_reasons) + ')' if packet.full_review_reasons else ''}; "
          f"{packet.changed_file_count} files changed, {packet.unchanged_file_count} unchanged, {packet.changed_line_count} lines")
    for change in packet.changes:
        print(f"  {change.change:8s} {change.path} +{change.added_lines} -{change.removed_lines}{' (truncated)' if change.truncated else ''}")
    print(f"history {[f'v{h.version} {h.status}' for h in packet.history]}")
    for ruling in packet.rulings:
        print(f"  ruling v{ruling.version} {ruling.court} {ruling.resolution} {ruling.decided_at:%m-%d %H:%M} | {ruling.reason[:150]}")
    for finding in packet.findings:
        print(f"  finding v{finding.version} {finding.outcome} {finding.reviewer} {finding.recorded_at:%m-%d %H:%M} | {finding.reason[:150]}")
    print(f"L1 lineage text {len(lineage_l1_text(packet))} characters; packet {packet.packet_sha256[:16]} written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
