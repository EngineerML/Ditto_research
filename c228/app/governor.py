"""Run-wide spend governor: keep a run under the bench's priced-cost budget when its questions turn out costly.

Every finished request adds its model tokens, priced at the bench's published rates for the chat model
(openai/gpt-oss-20b: $0.07 / 1M prompt, $0.15 / 1M completion, scoregates/priced_cost.go), to a window of the
last WINDOW requests. The bench's full-factor reference is $0.50 per 350-case run, and at $1.00 it stops a run and
scores what is left 0. When the window's average cost per request passes LEAN_AT_USD (on pace for about $0.70 a
run), later model calls go out lean: low reasoning effort and at most LEAN_MAX_TOKENS output tokens. Past
TIGHT_AT_USD (on pace for about $1.00) the output cap drops to TIGHT_MAX_TOKENS. When the average falls back under
RELEASE_AT_USD the calls go out as before.

It never adds, drops or changes a model call's messages or tools, only the effort and the output cap, and it acts
only after MIN_REQUESTS requests. Ordinary runs (about $0.0007-0.0014 per request) never reach it.
HARNESS_GOVERNOR_LEAN_AT / HARNESS_GOVERNOR_RELEASE_AT override the thresholds for local practice only; nothing on
the served path sets them.
"""

from __future__ import annotations

import logging
import os
from collections import deque

log = logging.getLogger("harness.governor")

PROMPT_USD_PER_TOKEN = 70e-9
OUTPUT_USD_PER_TOKEN = 150e-9
WINDOW = 100
MIN_REQUESTS = 30
LEAN_AT_USD = float(os.environ.get("HARNESS_GOVERNOR_LEAN_AT", "0.0020"))
RELEASE_AT_USD = float(os.environ.get("HARNESS_GOVERNOR_RELEASE_AT", "0.0016"))
TIGHT_AT_USD = float(os.environ.get("HARNESS_GOVERNOR_TIGHT_AT", "0.0028"))
LEAN_EFFORT = "low"
LEAN_MAX_TOKENS = 4000
TIGHT_MAX_TOKENS = 1500  # a second step, when lean calls still keep the run on pace for about $1.00


class SpendGovernor:
    def __init__(self) -> None:
        self.costs: deque[float] = deque(maxlen=WINDOW)
        self.lean = False
        self.tight = False
        self.requests = 0

    def average(self) -> float:
        return sum(self.costs) / len(self.costs) if self.costs else 0.0

    def record(self, prompt_tokens: int, output_tokens: int) -> None:
        self.requests += 1
        self.costs.append(prompt_tokens * PROMPT_USD_PER_TOKEN + output_tokens * OUTPUT_USD_PER_TOKEN)
        if len(self.costs) < MIN_REQUESTS:
            return
        average = self.average()
        if self.lean and not self.tight and average > TIGHT_AT_USD:
            self.tight = True
            log.warning("spend governor: tight from request %d, average $%.5f per request", self.requests, average)
        elif self.tight and average < LEAN_AT_USD:
            self.tight = False
        if not self.lean and average > LEAN_AT_USD:
            self.lean = True
            log.warning("spend governor: lean from request %d, average $%.5f per request over the last %d", self.requests, average, len(self.costs))
        elif self.lean and average < RELEASE_AT_USD:
            self.lean = False
            self.tight = False
            log.warning("spend governor: released at request %d, average $%.5f per request", self.requests, average)

    def effort(self, effort: str | None) -> str | None:
        return LEAN_EFFORT if self.lean and effort in {"medium", "high", None} else effort

    def max_tokens(self, max_tokens: int | None) -> int | None:
        if not self.lean:
            return max_tokens
        cap = TIGHT_MAX_TOKENS if self.tight else LEAN_MAX_TOKENS
        return cap if max_tokens is None else min(max_tokens, cap)


GOVERNOR = SpendGovernor()
