"""Side-by-side trajectories of two traced practice runs on the same dataset.

    .venv/bin/python tools/trace_compare.py RUN_A RUN_B --seed 4242 --size small [--all]

For every case either run scored below 1 (or every case with --all): the question, the
answer key, and per run the score and grader notes, the lane, whether the needed records
were in the packet, each model call (purpose, effort, temperature, prompt and reply size,
reply excerpt, tool calls) and the final answer. Full prompts and replies go to
RUN_B/compare/<case>.md. Case and record ids are per-run aliases inside the harness, so
cases are matched by question text and records by their text.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from lab import data  # noqa: E402

ALIAS = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\bc[0-9a-f]{16}\b")
PURPOSES = [
    ("one word only: SEND or HOLD", "repeat check"), ("You look at one tool call before it is sent", "repeat check"),
    ("Which one of the listed tools should your first call use", "plan (which tool)"),
    ("You read one request and the results of the calls", "result read"),
    ("Before this message is answered, decide what in the user's stored", "recall turn"),
    ("You look things up in the user's records", "search pass"),
    ("List every record that is about the subject", "timeline pass"),
    ("put them in the order the user must have written them", "order pass"),
    ("Below are the latest passages of a longer thread", "latest passages draft"),
    ("which person is it asking about", "thread reading"),
    ("write the one short follow-up question", "follow-up question"),
    ("suggests a follow-up question your reply could offer", "rewrite with follow-up"),
    ("drafts of a reply to the message above", "final after drafts"),
    ("A separate reading pass saw only the records", "decide (with reading note)"),
]


def plain(text: str) -> str:
    return re.sub(r"\s+", " ", ALIAS.sub("<id>", text or "")).strip().lower()


def purpose(call: dict) -> str:
    msgs = call["messages"]
    last_user = next((m.get("content") or "" for m in reversed(msgs) if m.get("role") == "user"), "")
    system = next((m.get("content") or "" for m in msgs if m.get("role") == "system"), "")
    for needle, name in PURPOSES:
        if needle in last_user or needle in system[:400]:
            if name == "decide (with reading note)" and needle not in last_user:
                continue
            return name
    if call["settings"].get("tool_choice") == "none" and (call["settings"].get("temperature") or 0) > 0:
        return "draft"
    if any(m.get("role") == "tool" for m in msgs):
        return "turn after tool results"
    if system.startswith("You are Ditto. The records below"):
        return "action turn"
    if system.startswith("You are Ditto, the user's assistant with long-term memory. Answer the message from the user's saved notes"):
        return "short-path decide"
    return "decide"


def effort(settings: dict) -> str:
    r = settings.get("reasoning")
    return (r or {}).get("effort") if isinstance(r, dict) else (settings.get("reasoning_effort") or "-")


def load_run(run: Path):
    report = json.load(open(run / "report.json"))["report"]
    scores = {c["case_id"]: c for c in report["per_case"]}
    traces = [json.loads(line) for line in open(run / "trace.jsonl", encoding="utf-8")]
    return report, scores, traces


def match(case: data.Case, traces: list[dict]) -> dict | None:
    want = plain(case.text)
    best, ratio = None, 0.0
    for t in traces:
        r = difflib.SequenceMatcher(None, want, plain(t["user_input"])).ratio()
        if r > ratio:
            best, ratio = t, r
    return best if ratio >= 0.85 else None


def same_record(a: str, b: str) -> bool:
    # served text and the local dataset differ by typing noise, so compare loosely
    return difflib.SequenceMatcher(None, plain(a)[:120], plain(b)[:120]).ratio() >= 0.8


def evidence_in_packet(case: data.Case, trace: dict) -> str:
    if not case.needs:
        return "no labelled evidence"
    by_id = {r.pair_id: r for r in case.store}
    needed = [by_id[pid].prompt for pid in case.needs if pid in by_id]
    shown = [p[1] for p in trace.get("packet") or []]
    if not shown:
        # short and topic paths put records straight into the prompt
        prompt = plain(" ".join(m.get("content") or "" for c in trace["calls"][:3] for m in c["messages"]))
        hits = sum(1 for text in needed if plain(text)[:40] in prompt)
        return f"about {hits}/{len(needed)} needed records in the prompt (no packet)"
    hits = sum(1 for text in needed if any(same_record(text, s) for s in shown))
    return f"{hits}/{len(needed)} needed records in a packet of {len(shown)} ({trace.get('packet_chars')} chars)"


def describe(name: str, case: data.Case, row: dict | None, trace: dict | None, lines: list[str]) -> None:
    if row is None or trace is None:
        lines.append(f"  [{name}] no {'score' if row is None else 'trace'} for this case")
        return
    lines.append(f"  [{name}] score {row.get('score')}  called {row.get('called')}  lane {trace.get('lane')}  "
                 f"model calls {len(trace['calls'])}  {trace.get('seconds')}s")
    lines.append(f"      notes: {' | '.join(row.get('notes') or [])[:400]}")
    lines.append(f"      records: {evidence_in_packet(case, trace)}")
    for i, call in enumerate(trace["calls"], 1):
        s = call["settings"]
        tools = f" tools={len(call['tools'])}" if call["tools"] else ""
        calls = f" -> {[(c['name'], c['args']) for c in call['tool_calls']]}"[:300] if call["tool_calls"] else ""
        reply = re.sub(r"\s+", " ", call["reply"] or "")[:220]
        lines.append(f"      {i:2d}. {purpose(call):26s} effort={effort(s)} temp={s.get('temperature')}{tools} "
                     f"in={call['prompt_tokens']} out={call['completion_tokens']} finish={call['finish']}{calls}")
        if reply:
            lines.append(f"          reply: {reply}")
    lines.append(f"      final answer: {trace.get('answer')!r}")
    lines.append(f"      final text: {re.sub(r'\\s+', ' ', trace.get('final_text') or '')[:400]}")


def dump(path: Path, case: data.Case, runs: list[tuple[str, dict | None, dict | None]]) -> None:
    out = [f"# {case.phase}:{case.kind}", "", f"Question: {case.text}", "", f"Answer key: {case.answers or case.tools}", ""]
    for name, row, trace in runs:
        out += [f"## {name}", "", f"score {row.get('score') if row else None}, lane {trace.get('lane') if trace else None}", ""]
        if not trace:
            continue
        for i, call in enumerate(trace["calls"], 1):
            out += [f"### call {i}: {purpose(call)} ({json.dumps(call['settings'])})", ""]
            for m in call["messages"]:
                content = m.get("content")
                if m.get("tool_calls"):
                    content = (content or "") + "\n[tool calls] " + json.dumps(m["tool_calls"], ensure_ascii=False)
                out += [f"**{m.get('role')}**", "", "```", str(content), "```", ""]
            out += ["**reply**", "", "```", str(call["reply"]), "```", ""]
            if call["tool_calls"]:
                out += ["**tool calls**", "", "```", json.dumps(call["tool_calls"], ensure_ascii=False, indent=1), "```", ""]
    path.write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_a", type=Path)
    ap.add_argument("run_b", type=Path)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--size", default="small")
    ap.add_argument("--salt", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cases = data.load(args.seed, args.salt, args.size)
    rep_a, scores_a, traces_a = load_run(args.run_a)
    rep_b, scores_b, traces_b = load_run(args.run_b)
    print(f"A {args.run_a.name}: composite {rep_a['composite']:.3f} tool {rep_a['tool_mean']:.3f} memory {rep_a['memory_mean']:.3f}")
    print(f"B {args.run_b.name}: composite {rep_b['composite']:.3f} tool {rep_b['tool_mean']:.3f} memory {rep_b['memory_mean']:.3f}")
    folder = args.run_b / "compare"
    folder.mkdir(exist_ok=True)
    for case in cases:
        cid = case.key.rsplit("/", 1)[-1]
        row_a, row_b = scores_a.get(cid), scores_b.get(cid)
        low = [r for r in (row_a, row_b) if r is not None and (r.get("score") or 0) < 0.999]
        if not args.all and not low:
            continue
        t_a, t_b = match(case, traces_a), match(case, traces_b)
        lines = ["", "=" * 110, f"{case.phase}:{case.kind}  ({cid})  truth lane {case.lane}",
                 f"  Q: {case.text[:300]}", f"  answer key: {case.answers or list(case.tools)}"]
        describe("A", case, row_a, t_a, lines)
        describe("B", case, row_b, t_b, lines)
        print("\n".join(lines))
        dump(folder / f"{case.kind}_{cid}.md", case, [("A " + args.run_a.name, row_a, t_a), ("B " + args.run_b.name, row_b, t_b)])
    print(f"\nfull prompts per case: {folder}")


if __name__ == "__main__":
    main()
