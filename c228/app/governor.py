"""Run-wide spend governor: keep a run under the bench's run budget when its questions turn out costly.

Every finished request adds its model tokens, priced at the bench's published rates for the chat model
(openai/gpt-oss-20b: $0.07 / 1M prompt, $0.15 / 1M completion, scoregates/priced_cost.go), to the run's spend and to a
window of the last WINDOW requests. The bench's full-factor reference is $0.50 per 350-case run; at $1.00 it stops a
run and scores every case not yet run 0.

Later model calls go out lean (low reasoning effort, at most LEAN_MAX_TOKENS output tokens) once the run has spent
LEAN_SPENT_USD, or once the window's average passes ABUSE_AVERAGE_USD after the run has spent ABUSE_FLOOR_USD. They go
out tight (at most TIGHT_MAX_TOKENS) past TIGHT_SPENT_USD, or past TIGHT_AVERAGE_USD on the same floor. An ordinary
run costs about $0.26-0.35 with a window average of at most about $0.0021 (its multi-call tool cases come first), so it
never reaches either. Once set, lean and tight hold until the run ends; a pause of RUN_GAP_SECONDS between requests
starts a new run's count.

It never adds, drops or changes a model call's messages or tools, only the effort and the output cap. The
HARNESS_GOVERNOR_* variables override the thresholds for local practice only; nothing on the served path sets them.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque

log = logging.getLogger("harness.governor")

PROMPT_USD_PER_TOKEN = 70e-9
OUTPUT_USD_PER_TOKEN = 150e-9
WINDOW = 100
MIN_REQUESTS = 30
RUN_GAP_SECONDS = 600.0
LEAN_SPENT_USD = float(os.environ.get("HARNESS_GOVERNOR_LEAN_SPENT", "0.60"))
TIGHT_SPENT_USD = float(os.environ.get("HARNESS_GOVERNOR_TIGHT_SPENT", "0.80"))
ABUSE_FLOOR_USD = float(os.environ.get("HARNESS_GOVERNOR_ABUSE_FLOOR", "0.20"))
ABUSE_AVERAGE_USD = float(os.environ.get("HARNESS_GOVERNOR_ABUSE_AVERAGE", "0.0035"))
TIGHT_AVERAGE_USD = float(os.environ.get("HARNESS_GOVERNOR_TIGHT_AVERAGE", "0.0040"))
LEAN_EFFORT = "low"
LEAN_MAX_TOKENS = 4000
TIGHT_MAX_TOKENS = 1500


class SpendGovernor:
    def __init__(self, clock=time.monotonic) -> None:
        self.clock = clock
        self.costs: deque[float] = deque(maxlen=WINDOW)
        self.spent = 0.0
        self.requests = 0
        self.last_at: float | None = None
        self.lean = False
        self.tight = False

    def average(self) -> float:
        return sum(self.costs) / len(self.costs) if self.costs else 0.0

    def record(self, prompt_tokens: int, output_tokens: int) -> None:
        now = self.clock()
        if self.last_at is not None and now - self.last_at > RUN_GAP_SECONDS:
            self.__init__(self.clock)  # a new run
        self.last_at = now
        self.requests += 1
        cost = prompt_tokens * PROMPT_USD_PER_TOKEN + output_tokens * OUTPUT_USD_PER_TOKEN
        self.spent += cost
        self.costs.append(cost)
        average = self.average() if len(self.costs) >= MIN_REQUESTS else 0.0
        abusive = self.spent > ABUSE_FLOOR_USD
        # Once a run has shown it is costly it stays governed until the run ends: easing off would only spend again.
        tight = self.tight or self.spent > TIGHT_SPENT_USD or (abusive and average > TIGHT_AVERAGE_USD)
        lean = self.lean or tight or self.spent > LEAN_SPENT_USD or (abusive and average > ABUSE_AVERAGE_USD)
        if (lean, tight) != (self.lean, self.tight):
            log.warning("spend governor: lean=%s tight=%s at request %d, run spend $%.3f, average $%.5f per request", lean, tight, self.requests, self.spent, average)
        self.lean, self.tight = lean, tight

    def effort(self, effort: str | None) -> str | None:
        return LEAN_EFFORT if self.lean and effort in {"medium", "high", None} else effort

    def max_tokens(self, max_tokens: int | None) -> int | None:
        if not self.lean:
            return max_tokens
        cap = TIGHT_MAX_TOKENS if self.tight else LEAN_MAX_TOKENS
        return cap if max_tokens is None else min(max_tokens, cap)


GOVERNOR = SpendGovernor()
