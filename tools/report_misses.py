"""List the cases a practice run lost points on, with the gates that fired.

    python3 tools/report_misses.py practice/<run>/report.json [more reports ...]
"""
import json
import sys

GATES = ("metamorphic_consistency", "tool_efficiency", "conversational_sanity", "memory_over_call")


def show(path: str) -> None:
    r = json.load(open(path))["report"]
    d = r["details"]
    print(f"== {path}")
    print(f"composite {r['composite']:.3f}  tool {r['tool_mean']:.3f}  memory {r['memory_mean']:.3f}  "
          + "  ".join(f"{g}={d.get(g)}" for g in GATES if not isinstance(d.get(g), dict))
          + (f"  over_call={json.dumps(d.get('memory_over_call'))[:160]}" if isinstance(d.get("memory_over_call"), dict) else ""))
    for c in r.get("per_case") or []:
        score = c.get("score")
        if score is None or score >= 0.999:
            continue
        what = c.get("question_type") or c.get("category") or c.get("kind")
        notes = " | ".join(c.get("notes") or [])[:300]
        answer = (c.get("answer") or c.get("final_text") or "")[:120].replace("\n", " ")
        print(f"  {score:.2f} {c.get('kind', '')}:{what} | expected {str(c.get('expected') or c.get('expected_answer'))[:60]!r} | got {answer!r}")
        if notes:
            print(f"       notes: {notes}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        show(p)
