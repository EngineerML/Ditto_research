"""Every trajectory of the gate questions (program twin rewordings and conversational-sanity slices) in
the runs of one or more v14 seeds, laid out per twin group and per conversational question.

    .venv/bin/python tools/gate_review.py OUT_DIR SEED [SEED ...] [--since 20261028T0744]

Traces carry the request's own id, not the dataset id, and the scorer serves its own typo surface, so a
trace is matched to its question by text: every (trace, question) pair is scored and assigned greedily,
best first, one trace per question. Each match is then checked by regrading the trace's answer with
grade.Memory (tools/regrade) against the run's own verdict; a disagreement is flagged in the output.

Writes OUT_DIR/review_<seed>.md (per group: the rewordings, and per run each one's verdict, answer,
which shared steps it reused and every model call) and OUT_DIR/summary.md (split groups and
conversational slices per run).
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from lab import data  # noqa: E402
from trace_compare import purpose  # noqa: E402

CONV = ("conversational-chitchat", "conversational-declarative", "declarative-behavior")
CASE_FILE = re.compile(r"\bc[0-9a-f]{16}\b")
SHARED = ("order pass", "shared draft", "final check", "short path", "statement", "kept", "follow-up", "rewrite")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text or "").lower())).strip()


def runs_for(seed: int, since: str) -> list[Path]:
    out = []
    for d in sorted(glob.glob(str(HERE / "practice" / "2026*_full*"))):
        path = Path(d)
        if path.name < since or "merged" in path.name or not path.name.endswith(("_full", "_full_rerun")) or not (path / "report.json").is_file() or not (path / "trace.jsonl").is_file():
            continue
        if int(json.load(open(path / "report.json")).get("seed") or 0) == seed:
            out.append(path)
    return out


def assign(cases: dict[str, dict], traces: list[dict]) -> dict[str, dict]:
    """Case id -> trace, best text matches first, each trace and case used once."""
    scored = []
    for cid, c in cases.items():
        q = norm(c["question"])
        # the scorer words each rewording its own way, but a case-file id is served exactly
        ids = set(CASE_FILE.findall(c["question"]))
        for i, t in enumerate(traces):
            bonus = 1.0 if ids and ids & set(CASE_FILE.findall(t["user_input"])) else 0.0
            scored.append((bonus + difflib.SequenceMatcher(None, q, norm(t["user_input"])).ratio(), cid, i))
    out, used = {}, set()
    for ratio, cid, i in sorted(scored, reverse=True):
        if cid in out or i in used or ratio < 0.4:
            continue
        out[cid] = traces[i]
        used.add(i)
    return out


def regrade(pairs: list[tuple[dict, dict]]) -> list[float]:
    lines = [json.dumps({"case": c, "final_text": t.get("final_text") or "", "answer": t.get("answer") or "", "run_score": -1, "match": 1}) for c, t in pairs]
    if not lines:
        return []
    out = subprocess.run(["go", "run", "."], cwd=HERE / "tools" / "regrade", input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout
    return [float(json.loads(line)["v14"]) for line in out.splitlines()]


def one_line(text: str, width: int) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:width]


def trace_lines(t: dict | None) -> list[str]:
    if t is None:
        return ["      (no trace matched)"]
    out = [f"      lane {t.get('lane')}; events: {one_line('; '.join(e for e in t.get('events') or [] if any(k in e for k in SHARED)), 600)}"]
    for i, call in enumerate(t["calls"], 1):
        calls = f" -> {one_line(json.dumps([(c['name'], c['args']) for c in call['tool_calls']], ensure_ascii=False), 200)}" if call["tool_calls"] else ""
        out.append(f"      {i}. {purpose(call)}{calls}: {one_line(call['reply'], 260)}")
    out.append(f"      final: {one_line(t.get('final_text'), 500)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("seeds", nargs="+", type=int)
    ap.add_argument("--since", default="20261028T0744")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data.BENCH = 14
    summary = ["| seed | run | twin groups | split | metric | chitchat | declarative | behavior | match check |", "|---|---|---|---|---|---|---|---|---|"]
    for seed in args.seeds:
        d = json.load(open(data.dataset_path(seed, 0, "full")))
        cases = {c["id"]: c for c in d["memory_cases"] if c.get("twin_group") or c["question_type"] in CONV}
        runs = []
        for path in runs_for(seed, args.since):
            rows = {r["case_id"]: r for r in json.load(open(path / "report.json"))["report"]["per_case"]}
            traces = [json.loads(line) for line in open(path / "trace.jsonl", encoding="utf-8")]
            # every question of the run takes part, so no trace is left for a look-alike to take
            everything = {c["id"]: c for c in d["memory_cases"] if c["id"] in rows}
            matched = {cid: t for cid, t in assign(everything, traces).items() if cid in cases}
            ids = list(matched)
            grades = dict(zip(ids, regrade([(cases[cid], matched[cid]) for cid in ids])))
            bad = [cid for cid in ids if (grades[cid] >= 0.999) != (str(rows[cid].get("correct")) == "True") and cases[cid]["question_type"] not in CONV]
            runs.append((path.name[:16], rows, matched, grades, bad))
        lines = [f"# Gate questions, seed {seed}", ""]
        groups = defaultdict(list)
        for cid, c in cases.items():
            if c.get("twin_group"):
                groups[c["twin_group"]].append(cid)
        for name, rows, matched, grades, bad in runs:
            verdicts = {g: [str(rows[cid].get("correct")) == "True" for cid in members if cid in rows] for g, members in groups.items()}
            split = sum(1 for v in verdicts.values() if len(set(v)) > 1)
            sl = []
            for kind in CONV:
                v = [str(rows[cid].get("correct")) == "True" for cid, c in cases.items() if c["question_type"] == kind and cid in rows]
                sl.append(f"{sum(v)}/{len(v)}")
            summary.append(f"| {seed} | {name} | {len(groups)} | {split} | {1 - split / max(1, len(groups)):.3f} | {' | '.join(sl)} | {len(matched)} matched, {len(bad)} disagree |")
        lines += ["## Twin groups", ""]
        for g, members in sorted(groups.items(), key=lambda x: cases[x[1][0]]["question_type"]):
            first = cases[members[0]]
            verdict_rows = []
            for name, rows, *_ in runs:
                verdict_rows.append(f"{name}: " + " ".join("–" if cid not in rows else "✓" if str(rows[cid].get("correct")) == "True" else "✗" for cid in members))
            lines += [f"### {first['question_type']} {g}: key {first.get('expected_answer')!r}", "", "Verdicts per run (rewordings in order): " + "; ".join(verdict_rows), ""]
            for cid in members:
                c = cases[cid]
                lines.append(f"- {cid}: {one_line(c['question'], 400)}")
                for name, rows, matched, grades, bad in runs:
                    if cid not in rows:
                        continue
                    r = rows[cid]
                    flag = " MATCH?" if cid in bad else ""
                    lines.append(f"  - {name}: correct {r.get('correct')} score {r.get('score')} relation {r.get('relation')}{flag}; grader: {one_line(' | '.join(n for n in eval(r.get('notes') or '[]') if 'trajectory' not in n), 300) if isinstance(r.get('notes'), str) else r.get('notes')}")
                    lines += trace_lines(matched.get(cid))
            lines.append("")
        lines += ["## Conversational sanity", ""]
        for kind in CONV:
            for cid, c in cases.items():
                if c["question_type"] != kind:
                    continue
                lines.append(f"### {kind} {cid}: key {c.get('expected_answer')!r}")
                lines.append(f"Message: {one_line(c['question'], 600)}")
                for name, rows, matched, grades, bad in runs:
                    r = rows.get(cid, {})
                    lines.append(f"  - {name}: correct {r.get('correct')} score {r.get('score')}; grader: {r.get('notes')}")
                    lines += trace_lines(matched.get(cid))
                lines.append("")
        (args.out / f"review_{seed}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
