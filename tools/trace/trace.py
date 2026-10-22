"""Local-practice trace of every model call. Copied into an image by tools/add_trace.py only.

Off unless HARNESS_TRACE_DIR is set. Writes one JSON line per case to
$HARNESS_TRACE_DIR/trace.jsonl: the request, the lane, the record packet, every chat call
with its full messages, offered tool names, sampling settings and reply, and the final
answer. Nothing here feeds back into inference.
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextvars import ContextVar
from typing import Any

_CASE: ContextVar[dict[str, Any] | None] = ContextVar("practice_trace", default=None)
_LOCK = threading.Lock()


def _dir() -> str:
    return os.environ.get("HARNESS_TRACE_DIR", "").strip()


def begin(req: Any):
    if not _dir():
        return None
    return _CASE.set({"case_id": req.case_id, "user_id": req.user_id, "user_input": req.user_input,
                      "system_prompt": req.system_prompt, "tools": [t.name for t in req.tools],
                      "started": time.time(), "calls": []})


def note(**fields: Any) -> None:
    case = _CASE.get()
    if case is not None:
        case.update(fields)


def call(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None, payload: dict[str, Any], result: Any) -> None:
    case = _CASE.get()
    if case is None:
        return
    case["calls"].append({
        "at": round(time.time() - case["started"], 2),
        "settings": {k: payload.get(k) for k in ("temperature", "seed", "max_tokens", "reasoning_effort", "reasoning", "tool_choice")},
        "tools": [t["function"]["name"] for t in tools or []],
        "messages": [dict(m) for m in messages],  # the harness keeps appending to this list
        "reply": result.content,
        "tool_calls": [{"name": c.name, "args": c.args} for c in result.tool_calls],
        "finish": result.finish_reason,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    })


def end(token) -> None:
    if token is None:
        return
    case = _CASE.get()
    _CASE.reset(token)
    if case is None:
        return
    case["seconds"] = round(time.time() - case.pop("started"), 2)
    line = json.dumps(case, ensure_ascii=False, default=str)
    with _LOCK, open(os.path.join(_dir(), "trace.jsonl"), "a", encoding="utf-8") as out:
        out.write(line + "\n")
