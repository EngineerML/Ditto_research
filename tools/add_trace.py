"""Copy a harness source tree and add the practice trace hooks (tools/trace/trace.py).

The same hooks go into Hades and into our harness, so their traces compare like for like.
The copy is for local practice images only; the committed harness has no trace code.

    python3 tools/add_trace.py SRC_DIR OUT_DIR
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def patch(path: Path, edits: list[tuple[str, str]]) -> None:
    text = path.read_text()
    for pattern, replacement in edits:
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
        if count != 1:
            raise SystemExit(f"{path}: hook point not found: {pattern}")
    path.write_text(text)


def main(src: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    app = out / "app"
    shutil.copy(HERE / "trace" / "trace.py", app / "trace.py")
    patch(app / "llm.py", [
        (r"^from app import audit$", "from app import audit, trace"),
        (r"^(\s+)audit\.record\(messages, tools, result\)$", r"\g<0>\n\1trace.call(messages, tools, payload, result)"),
    ])
    patch(app / "engine" / "agent.py", [
        (r"^from app\.audit import CURRENT, Journal$", "\\g<0>\nfrom app import trace"),
        (r"^(\s+)token = CURRENT\.set\(journal\)$", r"\g<0>\n\1trace_token = trace.begin(req)"),
        (r"^(\s+)CURRENT\.reset\(token\)$", r"\g<0>\n\1trace.end(trace_token)"),
        (r"^(\s+)outcome = await run_action\(engine, req, packet, deadline, lane\.reason, lead\)$",
         r"\1trace.note(packet=[[c.pair.pair_id, c.pair.prompt[:160]] for c in packet.records], packet_chars=packet.chars)\n\g<0>"),
        (r"^(\s+)latency_ms = int\(\(time\.monotonic\(\) - started\) \* 1000\)$",
         r"\1trace.note(lane=f'{lane.name}:{lane.reason}', events=list(outcome.events), answer=outcome.answer, final_text=outcome.content, model_calls=outcome.model_calls)\n\g<0>"),
    ])
    patch(app / "engine" / "records.py", [
        (r"^from __future__ import annotations$", "\\g<0>\n\nfrom app import trace"),
        (r"^(\s+)outcome\.events\.append\(f\"packet records=.*$",
         r"\g<0>\n\1trace.note(packet=[[c.pair.pair_id, c.pair.prompt[:160]] for c in packet.records], packet_chars=packet.chars)"),
    ])
    print(f"traced copy of {src} at {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
