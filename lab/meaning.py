"""Meaning search over a case's records: whole records, and paragraphs of long records."""
from __future__ import annotations

import re

import numpy as np

from lab.data import Case
from lab.embed import Embedder

LONG_RECORD_CHARS = 2000
PARAGRAPH = re.compile(r"\n\s*\n")


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in PARAGRAPH.split(text) if p.strip()]


class Meaning:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._records: dict[int, tuple[list[str], np.ndarray]] = {}
        self._chunks: dict[int, tuple[list[tuple[str, str]], np.ndarray]] = {}
        self._queries: dict[str, np.ndarray] = {}

    def query(self, text: str) -> np.ndarray:
        if text not in self._queries:
            self._queries[text] = self.embedder.vectors([text])[0]
        return self._queries[text]

    def queries(self, texts: list[str]) -> None:
        todo = [t for t in dict.fromkeys(texts) if t not in self._queries]
        for t, v in zip(todo, self.embedder.vectors(todo)):
            self._queries[t] = v

    def record_matrix(self, case: Case) -> tuple[list[str], np.ndarray]:
        key = id(case.store)
        if key not in self._records:
            self._records[key] = ([r.pair_id for r in case.store], self.embedder.vectors([r.text for r in case.store]))
        return self._records[key]

    def chunk_matrix(self, case: Case) -> tuple[list[tuple[str, str]], np.ndarray]:
        """(pair_id, paragraph) for every paragraph of every long record."""
        key = id(case.store)
        if key not in self._chunks:
            chunks = [(r.pair_id, p) for r in case.store if len(r.text) > LONG_RECORD_CHARS for p in paragraphs(r.prompt)]
            vectors = self.embedder.vectors([p for _, p in chunks]) if chunks else np.zeros((0, 768), dtype=np.float32)
            self._chunks[key] = (chunks, vectors)
        return self._chunks[key]

    def order(self, case: Case, query: str | None = None) -> list[str]:
        ids, matrix = self.record_matrix(case)
        scores = matrix @ self.query(query or case.text)
        return [ids[i] for i in np.argsort(-scores, kind="stable")]

    def scores(self, case: Case, query: str | None = None) -> dict[str, float]:
        ids, matrix = self.record_matrix(case)
        return dict(zip(ids, (matrix @ self.query(query or case.text)).tolist()))

    def best_chunks(self, case: Case, pair_id: str, limit: int) -> list[str]:
        chunks, matrix = self.chunk_matrix(case)
        rows = [i for i, (pid, _) in enumerate(chunks) if pid == pair_id]
        if not rows:
            return []
        scores = matrix[rows] @ self.query(case.text)
        keep = sorted(np.argsort(-scores)[:limit].tolist())
        return [chunks[rows[i]][1] for i in keep]
