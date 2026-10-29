"""Copy a dan0l-layout harness (dan0l v24's release, or combined/) and add the practice trace hooks.

    python3 tools/add_trace_dan0l.py SRC_DIR OUT_DIR

The hooks are tools/trace/trace.py, as in tools/add_trace.py for the Hades layout:
- every model call, wrapped around OpenAICompatLLM.chat, with its messages, tools, settings,
  reply and token counts, failed calls included;
- per case: the lane, the events, the answer and final text, and the records each path put
  in front of the deciding model (records packet, action packet, topic notes or program notes).
HARNESS_PROVIDER_PREFS (JSON) replaces the OpenRouter provider preferences, so two images can
be run on one pinned provider. HARNESS_REPLAY_WRITES (app/replay.py) puts back an earlier
run's tool-phase memory writes after the first seed, for re-running a few of its questions.
Copies for local practice images only.
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LLM_TAIL = '''

# --- practice trace (tools/add_trace_dan0l.py) ---
import json as _json
import os as _os

from . import trace as _trace

if _os.environ.get("HARNESS_PROVIDER_PREFS", "").strip():
    RELAY_PROVIDER_PREFERENCES.clear()
    RELAY_PROVIDER_PREFERENCES.update(_json.loads(_os.environ["HARNESS_PROVIDER_PREFS"]))

_untraced_chat = OpenAICompatLLM.chat


async def _traced_chat(self, messages, tools, **kwargs):
    try:
        result = await _untraced_chat(self, messages, tools, **kwargs)
    except LLMError as exc:
        _trace.failed(messages, tools, kwargs, exc)
        raise
    _trace.call(messages, tools, kwargs, result)
    return result


OpenAICompatLLM.chat = _traced_chat
'''


REPLAY = '''"""Re-run support (tools/add_trace_dan0l.py): put back the memory writes an earlier run's agent made.

HARNESS_REPLAY_WRITES names a JSON-lines file from tools/replay_writes.py. Its writes are applied
once, right after the first /seed (the tool-phase world), to that seed's user, as the original
run's tool phase made them: save_memory adds a saved record, update_memory rewrites the record
whose text matches. Record ids are blinded per run, so the original text is the key.
"""
import hashlib
import json
import logging
import os

from .tools import SAVED_PAIR_ID

_applied = False


def after_seed(store, user_id) -> None:
    global _applied
    path = os.environ.get("HARNESS_REPLAY_WRITES", "").strip()
    if _applied or not path:
        return
    _applied = True
    log = logging.getLogger("harness.replay")
    by_text = {p.prompt: p.pair_id for p in store.all_pairs(user_id)}
    for line in open(path, encoding="utf-8"):
        write = json.loads(line)
        if write["op"] == "save":
            pair_id = SAVED_PAIR_ID.format(digest=hashlib.sha256(write["content"].encode()).hexdigest()[:16])
            done = store.save_pair(user_id, pair_id, write["content"], write["timestamp"])
        else:
            pair_id = by_text.get(write["target"])
            if pair_id is None:  # a shown record may have been cut short: take a unique prefix match
                head = write["target"].rstrip(".\\u2026 ")
                hits = [pid for text, pid in by_text.items() if text.startswith(head)]
                pair_id = hits[0] if len(hits) == 1 else None
            done = pair_id is not None and store.rewrite_pair(user_id, pair_id, write["content"])
        log.info("replayed %s from case %s: %s", write["op"], write["case"], "applied" if done else "NOT APPLIED")
'''


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
    trace = (HERE / "trace" / "trace.py").read_text()
    trace += '''

def failed(messages, tools, payload, error) -> None:
    case = _CASE.get()
    if case is None:
        return
    case["calls"].append({"at": round(time.time() - case["started"], 2),
                          "settings": {k: payload.get(k) for k in ("temperature", "seed", "max_tokens", "reasoning_effort", "tool_choice")},
                          "tools": [t["function"]["name"] for t in tools or []], "messages": [dict(m) for m in messages],
                          "reply": "", "tool_calls": [], "finish": "llm-error: " + str(error)[:300],
                          "prompt_tokens": 0, "completion_tokens": 0})
'''
    (app / "trace.py").write_text(trace)
    (app / "llm.py").write_text((app / "llm.py").read_text() + LLM_TAIL)
    ids = "[[c.pair.pair_id, c.pair.prompt[:160]] for c in packet.records]"
    patch(app / "agent.py", [
        (r"^(\s+)started = time\.monotonic\(\)$", r"\g<0>\n\1trace_token = trace.begin(req)"),
        (r"^(\s+)outcome = await run_action\(engine, req, packet, deadline, lane\.reason, lead\)$",
         rf"\1trace.note(packet={ids}, packet_chars=packet.chars, path='action+topic' if lead else 'action')\n\g<0>"),
        (r"^(\s+)latency_ms = int\(\(time\.monotonic\(\) - started\) \* 1000\)$",
         r"\1trace.note(lane=f'{lane.name}:{lane.reason}', events=list(outcome.events), answer=outcome.answer, final_text=outcome.content, model_calls=outcome.model_calls)\n\g<0>"),
        (r"^(\s+)return RunResponse\(", r"\1trace.end(trace_token)\n\g<0>"),
        (r"^from __future__ import annotations$", "\\g<0>\n\nfrom . import trace"),
    ])
    patch(app / "records.py", [
        (r"^from __future__ import annotations$", "\\g<0>\n\nfrom . import trace"),
        (r"^(\s+)outcome\.events\.append\(f\"packet records=.*$", rf"\g<0>\n\1trace.note(packet={ids}, packet_chars=packet.chars, path='records')"),
    ])
    patch(app / "short.py", [
        (r"^from __future__ import annotations$", "\\g<0>\n\nfrom . import trace"),
        (r"^(\s+)outcome\.events\.append\(f\"short path records=.*$", r"\g<0>\n\1trace.note(packet=[[p.pair_id, p.prompt[:160]] for p in records], path='program')"),
        (r"^(\s+)draft = (?:.* else )?await self\.latest_draft\(req, notes, ",
         r"\1trace.note(packet=[[p.pair_id, p.prompt[:160]] for p in notes], path='topic')\n\g<0>"),
    ])
    (app / "replay.py").write_text(REPLAY)
    patch(app / "main.py", [
        (r"^(\s+)return AsciiJSONResponse\(SeedResponse\(", r"\1replay.after_seed(app.state.store, body.user_id)\n\g<0>"),
        (r"^from __future__ import annotations$", "\\g<0>\n\nfrom . import replay"),
    ])
    print(f"traced copy of {src} at {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
