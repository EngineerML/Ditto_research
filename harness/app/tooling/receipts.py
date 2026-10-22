"""Execution outcomes, immutable receipts and repeat-authorization contract."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


COMPLETED = "completed"
DELIVERY_UNKNOWN = "delivery_unknown"
DELIVERED_FAILED = "delivered_failed"
NOT_DELIVERED = "not_delivered"
BLOCKED = "blocked_before_execution"
SEND = "SEND"
HOLD = "HOLD"
REPEAT_OUTCOMES = {COMPLETED: "already ran (its result is above)", DELIVERY_UNKNOWN: "was already sent and no result came back (whether it ran is unknown)"}


@dataclass(frozen=True)
class Receipt:
    name: str
    args: dict[str, Any]
    state: str
    output: str


Authorize = Callable[[str, dict[str, Any], str, list[Receipt]], Awaitable[str | None]]


def call_identity(name: str, args: dict[str, Any]) -> str:
    return name + json.dumps(args, sort_keys=True, ensure_ascii=False)
