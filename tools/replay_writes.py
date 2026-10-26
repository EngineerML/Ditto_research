"""Write out the memory writes a traced run's agent made, for a re-run to put back.

    .venv/bin/python tools/replay_writes.py RUN_DIR OUT.jsonl [--skip IDS] [--seed S] [--size full]

During the tool phase dan0l-layout agents mirror each completed save_memory / update_memory
into their own store, and later questions read that store. A re-run of a few questions starts
from a fresh container, so the harness (HARNESS_REPLAY_WRITES, see tools/add_trace_dan0l.py)
replays these writes after the first seed. Writes come from the run's trace, kept only for
cases whose report shows the call observed at the tool endpoint; update targets are the text
of the record the model was shown under that pair id, since ids are blinded per run. --skip
leaves out the writes of the questions being re-run, which make them again themselves.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from flag_failed_calls import case_ids, graded_rows, latencies  # noqa: E402
from lab import data  # noqa: E402

WRITES = ("save_memory", "update_memory")
FOLLOW_LINE = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d),\d+ INFO harness\.tools tool (\w+) completed at the endpoint and this user's own store now follows it")


def shown_text(trace: dict, pair_id: str) -> str | None:
    """The record text the model saw under pair_id (the `user` side of a shown record)."""
    for call in trace["calls"]:
        for message in call["messages"]:
            content = message.get("content")
            text = content if isinstance(content, str) else json.dumps(content or "")
            at = text.find(f'"pairID": "{pair_id}"')
            if at < 0:
                continue
            start = text.rfind("{", 0, at)
            try:
                return json.JSONDecoder().raw_decode(text[start:])[0]["user"]
            except (ValueError, KeyError):
                continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--skip", type=Path, help="case ids whose own writes are left out")
    ap.add_argument("--seed", type=int, default=3590624429364033488)
    ap.add_argument("--size", default="full")
    args = ap.parse_args()
    skip = set(args.skip.read_text().split()) if args.skip else set()
    rows = graded_rows(args.run)
    observed = {c["case_id"] for c in rows if c.get("observed") and set(c.get("called") or []) & set(WRITES)}
    follows = [m.groups() for m in map(FOLLOW_LINE.match, (args.run / "harness.log").read_text().splitlines()) if m]
    save_times = [f"{day}T{clock}Z" for day, clock, name in follows if name == "save_memory"]
    traces = [json.loads(line) for line in open(args.run / "trace.jsonl", encoding="utf-8")]
    ids = case_ids(traces, data.load(args.seed, 0, args.size), latencies(rows))
    writes, missing = [], 0
    for trace, cid in zip(traces, ids):
        calls = [tc for c in trace["calls"] for tc in c.get("tool_calls") or [] if tc["name"] in WRITES]
        if not calls:
            continue
        if cid not in observed:
            continue
        last = calls[-1]
        write = {"case": cid, "op": "save" if last["name"] == "save_memory" else "update", "content": last["args"].get("content", "")}
        if write["op"] == "update":
            write["target"] = shown_text(trace, last["args"].get("pair_id", ""))
            if write["target"] is None:
                print(f"{cid}: update target {last['args'].get('pair_id')} not found in the shown records", file=sys.stderr)
                missing += 1
                continue
        writes.append(write)
    for write in (w for w in writes if w["op"] == "save"):
        write["timestamp"] = save_times.pop(0) if save_times else ""
    if len(writes) + missing != len(follows):
        print(f"warning: {len(writes) + missing} writes found in the trace, harness log shows {len(follows)}", file=sys.stderr)
    kept = [w for w in writes if w["case"] not in skip]
    args.out.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w in kept))
    print(f"{len(kept)} writes to replay ({len(writes) - len(kept)} left to the re-run questions, {missing} unresolved) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
