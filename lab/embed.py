"""Embeddings on the model validators serve, with a disk cache and a spending cap.

Validators answer the harness's /api/embed with OpenRouter perplexity/pplx-embed-v1-0.6b
at 768 dimensions. Every text is embedded once ever: vectors live in
.cache/embeddings.sqlite under sha256(model, dims, text). Price on 2026-10-22 is
$0.004 per million input tokens, so the cap mostly guards against bugs.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from lab.data import ROOT

MODEL = "perplexity/pplx-embed-v1-0.6b"
DIMS = 768
URL = "https://openrouter.ai/api/v1/embeddings"
USD_PER_TOKEN = 0.004 / 1e6
CHARS_PER_TOKEN = 4
MAX_TEXT_CHARS = 12000      # what Hades sends per record
BATCH_TEXTS = 32
BATCH_CHARS = 40000         # the proxy drops very large bodies
RETRYABLE = (urllib.error.URLError, OSError, http.client.HTTPException, TimeoutError, KeyError, ValueError)
CACHE = ROOT / ".cache" / "embeddings.sqlite"


def api_key() -> str:
    env = ROOT / ".env.local"
    for line in env.read_text().splitlines() if env.is_file() else []:
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return os.environ.get("OPENROUTER_API_KEY", "")


class Embedder:
    def __init__(self, budget_usd: float = 0.10) -> None:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(CACHE)
        self.db.execute("CREATE TABLE IF NOT EXISTS vectors (h TEXT PRIMARY KEY, v BLOB NOT NULL)")
        self.budget = budget_usd
        self.spent = 0.0
        self.sent_chars = 0

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(f"{MODEL}|{DIMS}|{text}".encode()).hexdigest()

    def vectors(self, texts: list[str]) -> np.ndarray:
        texts = [t[:MAX_TEXT_CHARS] or " " for t in texts]
        keys = [self.key(t) for t in texts]
        found: dict[str, np.ndarray] = {}
        for start in range(0, len(keys), 500):
            chunk = keys[start:start + 500]
            rows = self.db.execute(f"SELECT h, v FROM vectors WHERE h IN ({','.join('?' * len(chunk))})", chunk).fetchall()
            found.update((h, np.frombuffer(v, dtype=np.float32)) for h, v in rows)
        missing = list(dict.fromkeys(t for t, k in zip(texts, keys) if k not in found))
        if missing:
            self._fetch(missing, found)
        return np.stack([found[k] for k in keys]) if keys else np.zeros((0, DIMS), dtype=np.float32)

    def _fetch(self, texts: list[str], found: dict[str, np.ndarray]) -> None:
        cost = sum(len(t) for t in texts) / CHARS_PER_TOKEN * USD_PER_TOKEN
        if self.spent + cost > self.budget:
            raise RuntimeError(f"embedding {len(texts)} texts would cost ${cost:.4f}, over the ${self.budget:.2f} cap")
        key = api_key()
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY missing from .env.local")
        batch: list[str] = []
        for text in texts + [None]:
            if text is not None and (not batch or (len(batch) < BATCH_TEXTS and sum(map(len, batch)) + len(text) <= BATCH_CHARS)):
                batch.append(text)
                continue
            if batch:
                for t, v in zip(batch, self._post(batch, key)):
                    vector = np.asarray(v, dtype=np.float32)
                    vector /= max(float(np.linalg.norm(vector)), 1e-9)
                    found[self.key(t)] = vector
                    self.db.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?)", (self.key(t), vector.tobytes()))
                self.db.commit()
                self.sent_chars += sum(map(len, batch))
                self.spent += sum(map(len, batch)) / CHARS_PER_TOKEN * USD_PER_TOKEN
            batch = [text] if text is not None else []

    @staticmethod
    def _post(batch: list[str], key: str, attempts: int = 6) -> list[list[float]]:
        body = json.dumps({"model": MODEL, "input": batch, "dimensions": DIMS, "encoding_format": "float"}).encode()
        for attempt in range(attempts):
            req = urllib.request.Request(URL, data=body, method="POST",
                                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.load(resp)["data"]
                return [row["embedding"] for row in sorted(data, key=lambda r: r["index"])]
            except urllib.error.HTTPError as exc:
                if exc.code in (400, 401, 402, 403) or attempt == attempts - 1:
                    raise RuntimeError(f"embedding request refused: HTTP {exc.code} {exc.read()[:200]!r}") from None
            except RETRYABLE:
                if attempt == attempts - 1:
                    raise
            time.sleep(2 * (attempt + 1))
        return []
