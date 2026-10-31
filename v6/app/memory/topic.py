from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from ..protocol import MemoryPair
from .retrieval import STOPWORDS, tokens

PARAGRAPH_RE = re.compile(r"\n\s*\n")
MAX_PHRASE_WORDS = 6
TOPIC_DENSITY = 3


@dataclass(frozen=True)
class Topic:
    phrase: tuple[str, ...]
    records: int
    densest: int
    paragraphs: int


def edits(a: str, b: str) -> int:
    rows = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        rows[i][0] = i
    for j in range(len(b) + 1):
        rows[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[len(a)][len(b)]


def typo_budget(word: str) -> int:
    return 0 if len(word) <= 2 else 1 if len(word) <= 5 else 2


def typo_of(word: str, seen: str) -> bool:
    if word == seen:
        return True
    budget = typo_budget(word)
    return budget > 0 and abs(len(word) - len(seen)) <= budget and edits(word, seen) <= budget


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in PARAGRAPH_RE.split(text) if part.strip()]


def holds(phrase: tuple[str, ...], words: list[str], spellings: dict[str, frozenset[str]]) -> bool:
    size = len(phrase)
    for start in range(len(words) - size + 1):
        if all(words[start + k] in spellings[phrase[k]] for k in range(size)):
            return True
    return False


class TopicIndex:
    def __init__(self, pairs: list[MemoryPair]) -> None:
        self.pairs = pairs
        self.parts = [[(text, tokens(text)) for text in paragraphs(pair.prompt)] for pair in pairs]
        self.where: dict[str, set[tuple[int, int]]] = {}
        self.by_length: dict[int, set[str]] = {}
        for index, parts in enumerate(self.parts):
            for spot, (_, words) in enumerate(parts):
                for word in words:
                    self.where.setdefault(word, set()).add((index, spot))
        for word in self.where:
            if word:
                self.by_length.setdefault(len(word), set()).add(word)

    def spellings(self, asked: list[str]) -> dict[str, frozenset[str]]:
        out: dict[str, frozenset[str]] = {}
        for word in set(asked):
            budget = typo_budget(word)
            pool = {seen for size in range(len(word) - budget, len(word) + budget + 1) for seen in self.by_length.get(size, ())}
            out[word] = frozenset(seen for seen in pool if typo_of(word, seen))
        return out

    def counts(self, phrase: tuple[str, ...], spellings: dict[str, frozenset[str]]) -> Counter[int]:
        spots: set[tuple[int, int]] = set()
        for seen in spellings[phrase[0]]:
            spots |= self.where[seen]
        found: Counter[int] = Counter()
        for index, spot in spots:
            if holds(phrase, self.parts[index][spot][1], spellings):
                found[index] += 1
        return found

    def topic(self, question: str) -> Topic | None:
        asked = tokens(question)
        spellings = self.spellings(asked)
        best: tuple[tuple[int, int, int, int], tuple[str, ...], Counter[int]] | None = None
        for size in range(2, min(MAX_PHRASE_WORDS, len(asked)) + 1):
            for start in range(len(asked) - size + 1):
                phrase = tuple(asked[start : start + size])
                if phrase[0] in STOPWORDS or phrase[-1] in STOPWORDS or any(not spellings[word] for word in phrase):
                    continue
                found = self.counts(phrase, spellings)
                if len(found) < 2:
                    continue
                densest = max(found.values())
                rank = (min(densest, TOPIC_DENSITY), size, densest, sum(found.values()))
                if best is None or rank > best[0]:
                    best = (rank, phrase, found)
        if best is None:
            return None
        rank, phrase, found = best
        return Topic(phrase=phrase, records=len(found), densest=rank[2], paragraphs=rank[3])

    def excerpt(self, topic: Topic) -> list[MemoryPair]:
        spellings = self.spellings(list(topic.phrase))
        out: list[MemoryPair] = []
        for pair, parts in zip(self.pairs, self.parts):
            kept = [text for text, words in parts if holds(topic.phrase, words, spellings)]
            if kept:
                out.append(pair.model_copy(update={"prompt": "\n\n".join(kept), "response": ""}))
        return sorted(out, key=lambda pair: (pair.timestamp, pair.pair_id))
