from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import random
from array import array
from collections.abc import Iterable

import httpx

from app.protocol import MemoryPair

log = logging.getLogger("harness.embedding")

EMBED_PATH = "/api/embed"
EMBED_MODEL = "embeddinggemma"
MAX_INPUTS = 32
MAX_BATCH_CHARS = 60000
MAX_INPUT_CHARS = 12000
ATTEMPTS = 4
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
RRF_K = 60


class EmbeddingError(RuntimeError):
    pass


def record_text(pair: MemoryPair) -> str:
    return pair.prompt + "\n" + pair.response


def text_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def batches(texts: list[str]) -> Iterable[list[str]]:
    chunk: list[str] = []
    size = 0
    for text in texts:
        if chunk and (len(chunk) >= MAX_INPUTS or size + len(text) > MAX_BATCH_CHARS):
            yield chunk
            chunk, size = [], 0
        chunk.append(text)
        size += len(text)
    if chunk:
        yield chunk


def normalized(values: list[float]) -> array:
    norm = math.sqrt(math.sumprod(values, values))
    if not norm or not math.isfinite(norm):
        raise EmbeddingError("embedding vector has no direction")
    return array("f", (v / norm for v in values))


class Embedder:
    def __init__(self, base_url: str, http: httpx.AsyncClient, timeout_seconds: float) -> None:
        self.url = base_url.rstrip("/") + EMBED_PATH
        self.http = http
        self.timeout = timeout_seconds

    async def embed(self, texts: list[str]) -> list[array]:
        out: list[array] = []
        for chunk in batches([text[:MAX_INPUT_CHARS] for text in texts]):
            vectors = await self._post(chunk)
            if len(vectors) != len(chunk) and len(chunk) > 1:
                vectors = [vector for text in chunk for vector in await self._post([text])]
            if len(vectors) != len(chunk):
                raise EmbeddingError(f"embedding service returned {len(vectors)} vectors for {len(chunk)} inputs")
            out.extend(vectors)
        return out

    async def _post(self, chunk: list[str]) -> list[array]:
        problem = ""
        for attempt in range(ATTEMPTS):
            if attempt:
                await asyncio.sleep(min(8.0, 0.5 * 2 ** attempt) + random.random() * 0.25)
            try:
                response = await self.http.post(self.url, json={"model": EMBED_MODEL, "input": chunk}, timeout=self.timeout)
            except httpx.TransportError as exc:
                problem = f"transport: {exc!r}"
                continue
            if response.status_code in RETRY_STATUSES:
                problem = f"status {response.status_code}"
                continue
            if response.status_code != 200:
                raise EmbeddingError(f"embedding request refused: status {response.status_code}: {response.text[:300]}")
            try:
                vectors = response.json()["embeddings"]
            except (ValueError, KeyError, TypeError) as exc:
                raise EmbeddingError(f"embedding response unreadable: {exc!r}") from exc
            try:
                if not isinstance(vectors, list) or not vectors or len({len(v) for v in vectors}) != 1 or not vectors[0]:
                    raise EmbeddingError("embedding response does not match the inputs")
                return [normalized([float(x) for x in v]) for v in vectors]
            except (TypeError, ValueError) as exc:
                raise EmbeddingError(f"embedding response unreadable: {exc!r}") from exc
        raise EmbeddingError(f"embedding failed after {ATTEMPTS} attempts: {problem}")


def dense_order(question: array, pairs: list[MemoryPair], vectors: dict[str, array]) -> list[str]:
    scored = [(math.sumprod(question, vectors[key]), pair.pair_id) for pair in pairs if (key := text_key(record_text(pair))) in vectors and len(vectors[key]) == len(question)]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [pair_id for _, pair_id in scored]


def fuse(*orders: list[str]) -> list[str]:
    score: dict[str, float] = {}
    for order in orders:
        for rank, pair_id in enumerate(order, start=1):
            score[pair_id] = score.get(pair_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(score, key=lambda pair_id: -score[pair_id])
