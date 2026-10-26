"""Meaning router: the request's nearest example requests pick its lane when they agree.

`intents.tsv` holds hand-written example requests labelled `records` or `action`; none is
taken from a benchmark dataset. The request is embedded by the same embedding service as
the records, and its K nearest examples vote, weighted by similarity. The host acts on the
vote only when it is at least `sure` one way; otherwise the word rules in lane.py decide.
"""
from __future__ import annotations

import asyncio
import logging
import math
from array import array
from pathlib import Path

from app.memory.embedding import Embedder, EmbeddingError

log = logging.getLogger("harness.meaning")

BANK_PATH = Path(__file__).with_name("intents.tsv")
NEAREST = 5
LANES = ("records", "action")


def read_bank(path: Path = BANK_PATH) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        lane, text = line.split("\t", 1)
        if lane.strip() in LANES and text.strip():
            rows.append((lane.strip(), text.strip()))
    return rows


class IntentBank:
    def __init__(self, path: Path = BANK_PATH) -> None:
        self.rows = read_bank(path)
        self.vectors: list[array] | None = None
        self._lock = asyncio.Lock()

    async def _ready(self, embedder: Embedder) -> list[array]:
        async with self._lock:
            if self.vectors is None:
                self.vectors = await embedder.embed([text for _, text in self.rows])
            return self.vectors

    async def lane(self, embedder: Embedder, request: str) -> tuple[str, float] | None:
        """(lane, share of the vote) or None when the embedding service cannot answer."""
        if not self.rows or not request.strip():
            return None
        try:
            vectors = await self._ready(embedder)
            [asked] = await embedder.embed([request])
        except EmbeddingError as exc:
            log.warning("meaning router unavailable, word rules decide: %s", exc)
            return None
        scored = sorted(((math.sumprod(asked, vector), lane) for vector, (lane, _) in zip(vectors, self.rows)
                         if len(vector) == len(asked)), reverse=True)[:NEAREST]
        if not scored:
            return None
        weights = [(max(score, 0.0) + 1e-6, lane) for score, lane in scored]
        records = sum(weight for weight, lane in weights if lane == "records") / sum(weight for weight, _ in weights)
        return ("records", records) if records >= 0.5 else ("action", 1.0 - records)
