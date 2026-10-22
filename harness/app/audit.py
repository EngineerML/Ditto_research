"""Optional, observation-only completion journal for public local gate replay.

Uses the official starter log shape. It is miner-reported diagnostic evidence,
not a validator attestation. No journal value participates in inference.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import logging
import os
import threading
from typing import Any

from app.protocol import MemoryPair, RunRequest

CURRENT: ContextVar["Journal | None"] = ContextVar("completion_journal", default=None)
LOCK = threading.Lock()


@dataclass
class Journal:
    request: RunRequest
    records: list[MemoryPair]
    offers: set[str] = field(default_factory=set)
    harness: set[str] = field(default_factory=set)
    admitted: set[str] = field(default_factory=set)
    results: set[str] = field(default_factory=set)
    completions: list[dict[str, Any]] = field(default_factory=list)

    def record(self, messages, tools, result) -> None:
        self.offers.update(tool["function"]["name"] for tool in tools or [])
        for message in messages:
            content = message.get("content")
            if not isinstance(content, str):
                continue
            if message.get("role") == "tool":
                self.results.add(content)
            elif message.get("role") in {"system", "developer", "user"}:
                # Conservatively retain all prompt spans, including mixed
                # source/advice messages; exempt only originals actually seen.
                self.harness.add(content)
                for pair in self.records:
                    for original in (pair.prompt, pair.response):
                        original = original.strip()
                        if original and (original in content or json.dumps(original, ensure_ascii=False)[1:-1] in content):
                            self.admitted.add(original)
        self.completions.append({"text": result.content, "tool_calls": [
            {"name": call.name, "args": call.args} for call in result.tool_calls
        ]})

    def write(self, path: str) -> None:
        req = self.request
        value = {"case_id": req.case_id, "user_id": req.user_id or "default",
                 "bench_version": req.bench_version or 9, "user_input": req.user_input,
                 "catalog": [{"name": t.name, "description": t.description} for t in req.tools],
                 "tools_offered": sorted(self.offers), "harness_spans": sorted(self.harness),
                 "record_spans": sorted(self.admitted), "tool_results": sorted(self.results),
                 "completions": self.completions}
        with LOCK:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def record(messages, tools, result) -> None:
    journal = CURRENT.get()
    if journal is not None:
        try:
            journal.record(messages, tools, result)
        except Exception:
            logging.getLogger("harness.audit").exception("completion journal failed; inference result retained")
