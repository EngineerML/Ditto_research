"""The routing and selection designs under test.

Routers return "records" or "action". Selectors return the records (and, for
compressed long records, the paragraphs) a design would put in front of the model.

- hades:        Hades v6 lane rules / record pack, exactly as released (lab/hades.py)
- knn:          nearest labelled questions by meaning, from other seeds and salts
- combo:        knn when it is sure, Hades rules otherwise
- dense:        the k records closest in meaning, whole
- overhorizon:  rebuild of the owner's design: action lane takes nearly every record whole;
                records lane takes short records whole and only the closest paragraphs of
                long records, naming the long record's id
- union:        Hades pack + dense top k + full-text hits, under one character budget
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from lab import hades
from lab.data import Case
from lab.meaning import LONG_RECORD_CHARS, Meaning

RECORDS, ACTION = "records", "action"


@dataclass
class Pick:
    pair_ids: list[str]
    text: str
    chars: int
    compressed: set[str] = field(default_factory=set)
    path: str = ""


def whole(case: Case, ids: list[str]) -> Pick:
    by_id = {r.pair_id: r for r in case.store}
    kept = [i for i in dict.fromkeys(ids) if i in by_id]
    text = "\n".join(by_id[i].text for i in kept)
    return Pick(kept, text, len(text))


# ---------- routers

def route_hades(case: Case, worlds: hades.HadesWorld) -> tuple[str, str]:
    lane = hades.route(case, worlds)
    return (RECORDS if lane.name == hades.RECORDS else ACTION), lane.reason


class KNNRouter:
    def __init__(self, meaning: Meaning, train: list[Case], k: int = 9) -> None:
        self.meaning = meaning
        self.k = k
        meaning.queries([c.text for c in train])
        self.matrix = np.stack([meaning.query(c.text) for c in train])
        self.labels = np.array([1.0 if c.lane == RECORDS else 0.0 for c in train])

    def __call__(self, case: Case) -> tuple[str, float]:
        scores = self.matrix @ self.meaning.query(case.text)
        top = np.argsort(-scores)[: self.k]
        weights = np.maximum(scores[top], 0.0) + 1e-6
        share = float((weights * self.labels[top]).sum() / weights.sum())
        return (RECORDS, share) if share >= 0.5 else (ACTION, 1.0 - share)


def route_combo(case: Case, worlds: hades.HadesWorld, knn: KNNRouter, sure: float) -> tuple[str, str]:
    lane, confidence = knn(case)
    if confidence >= sure:
        return lane, f"knn {confidence:.2f}"
    return route_hades(case, worlds)


# ---------- selectors

def pick_hades(case: Case, lane: str, worlds: hades.HadesWorld, meaning: Meaning | None) -> Pick:
    reason = hades.route(case, worlds)
    if (lane == RECORDS) != (reason.name == hades.RECORDS):
        reason = hades.Lane(hades.RECORDS, "question") if lane == RECORDS else hades.Lane("action", "imperative")
    dense = (lambda c, q: meaning.order(c, q)) if meaning is not None else None
    sel = hades.select(case, reason, worlds, dense)
    pick = whole(case, sel.pair_ids)
    pick.path = sel.path
    return pick


def pick_dense(case: Case, meaning: Meaning, k: int) -> Pick:
    return whole(case, meaning.order(case)[:k])


def pick_overhorizon(case: Case, lane: str, meaning: Meaning, worlds: hades.HadesWorld,
                     action_k: int = 60, records_k: int = 24, long_paragraphs: int = 8) -> Pick:
    by_id = {r.pair_id: r for r in case.store}
    lexical = hades.lexical_order(case, worlds)
    dense = meaning.order(case)
    ranked = list(dict.fromkeys(interleave(dense, lexical)))
    if lane == ACTION:
        return whole(case, ranked[:action_k])
    kept, parts, compressed = [], [], set()
    for pid in ranked[:records_k]:
        record = by_id[pid]
        kept.append(pid)
        if len(record.text) > LONG_RECORD_CHARS:
            compressed.add(pid)
            parts.append(f"[long record {pid}]\n" + "\n".join(meaning.best_chunks(case, pid, long_paragraphs)))
        else:
            parts.append(record.text)
    text = "\n".join(parts)
    return Pick(kept, text, len(text), compressed)


def pick_union(case: Case, lane: str, worlds: hades.HadesWorld, meaning: Meaning, dense_k: int = 12,
               text_k: int = 8, budget: int = 48000, keep_short_paths: bool = False, need_anchor: bool = False) -> Pick:
    """keep_short_paths: leave Hades's short/topic paths as they are (what the harness does).
    need_anchor: widen only when the question names something the records hold (Hades's anchors)."""
    picked = pick_hades(case, lane, worlds, meaning)
    if keep_short_paths and picked.path in ("short", "topic"):
        return picked
    if need_anchor and not worlds.world(case)[1].rank(case.user, case.text)[1]:
        return picked
    base = picked.pair_ids
    extra = meaning.order(case)[:dense_k] + hades.full_text_hits(case, worlds, text_k)
    by_id = {r.pair_id: r for r in case.store}
    kept, used = [], 0
    for pid in dict.fromkeys(base + extra):
        size = len(by_id[pid].text)
        if used + size > budget and pid not in base:
            continue
        kept.append(pid)
        used += size
    return whole(case, kept)


def interleave(*orders: list[str]) -> list[str]:
    out: list[str] = []
    for items in zip(*orders):
        out.extend(items)
    return out
