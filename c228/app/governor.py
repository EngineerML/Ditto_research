"""Spend governor: cap the output of model calls only while recent questions are clearly abusive in cost.

Every finished request adds its model tokens, priced at the bench's published rates for the chat model
(openai/gpt-oss-20b: $0.07 / 1M prompt, $0.15 / 1M completion, scoregates/priced_cost.go), to a window of the last
WINDOW requests. The bench stops a run at $1.00 and scores every case not yet run 0.

While the window's average passes ABUSE_AVERAGE_USD (about 1.6 times the costliest stretch of an ordinary run, its
multi-call tool cases, at about $0.0022 per request), later calls go out lean: low reasoning effort and at most
LEAN_MAX_TOKENS output tokens; past TIGHT_AVERAGE_USD, at most TIGHT_MAX_TOKENS. When the average falls back under
RELEASE_AVERAGE_USD, calls go out as before. It reads nothing but this window, so how long the process has been up and
how many runs it has served never matter, and it acts only after MIN_REQUESTS requests.

It never adds, drops or changes a model call's messages or tools, only the effort and the output cap. The
HARNESS_GOVERNOR_* variables override the thresholds for local practice only; nothing on the served path sets them.
"""

from __future__ import annotations

import logging
import os
from collections import deque

log = logging.getLogger("harness.governor")

PROMPT_USD_PER_TOKEN = 70e-9
OUTPUT_USD_PER_TOKEN = 150e-9
WINDOW = 100
MIN_REQUESTS = 50
ABUSE_AVERAGE_USD = float(os.environ.get("HARNESS_GOVERNOR_ABUSE_AVERAGE", "0.0035"))
TIGHT_AVERAGE_USD = float(os.environ.get("HARNESS_GOVERNOR_TIGHT_AVERAGE", "0.0050"))
RELEASE_AVERAGE_USD = float(os.environ.get("HARNESS_GOVERNOR_RELEASE_AVERAGE", "0.0028"))
LEAN_EFFORT = "low"
LEAN_MAX_TOKENS = 4000
TIGHT_MAX_TOKENS = 1500


class SpendGovernor:
    def __init__(self) -> None:
        self.costs: deque[float] = deque(maxlen=WINDOW)
        self.requests = 0
        self.lean = False
        self.tight = False

    def average(self) -> float:
        return sum(self.costs) / len(self.costs) if self.costs else 0.0

    def record(self, prompt_tokens: int, output_tokens: int) -> None:
        self.requests += 1
        self.costs.append(prompt_tokens * PROMPT_USD_PER_TOKEN + output_tokens * OUTPUT_USD_PER_TOKEN)
        if len(self.costs) < MIN_REQUESTS:
            return
        average = self.average()
        lean, tight = self.lean, self.tight
        if average > TIGHT_AVERAGE_USD:
            lean = tight = True
        elif average > ABUSE_AVERAGE_USD:
            lean = True
        elif average < RELEASE_AVERAGE_USD:
            lean = tight = False
        if (lean, tight) != (self.lean, self.tight):
            log.warning("spend governor: lean=%s tight=%s at request %d, average $%.5f per request", lean, tight, self.requests, average)
        self.lean, self.tight = lean, tight

    def effort(self, effort: str | None) -> str | None:
        return LEAN_EFFORT if self.lean and effort in {"medium", "high", None} else effort

    def max_tokens(self, max_tokens: int | None) -> int | None:
        if not self.lean:
            return max_tokens
        cap = TIGHT_MAX_TOKENS if self.tight else LEAN_MAX_TOKENS
        return cap if max_tokens is None else min(max_tokens, cap)


GOVERNOR = SpendGovernor()
