from __future__ import annotations

from app.memory.packet import Packet
from app.memory.retrieval import UserIndex

CLOSEST_KINDS = frozenset("ecqnikb")
CLOSEST_MIN_TERMS = 2
CLOSEST_MIN_RECORDS = 2
CLOSEST_MAX_RECORDS = 8
CLOSEST_LONG_CHARS = 1500
CLOSEST_LONG_RECORDS = 2


def term_holders(index: UserIndex, key: str) -> set[str]:
    if key.startswith("b:"):
        words = tuple(key[2:].split())
        return set(index.bigrams.get(words, ())) if len(words) == 2 else set()
    return set(index.postings.get(key, ()))


def closest_records(index: UserIndex, anchors: dict[str, tuple[str, float]], packet: Packet) -> Packet:
    terms = [key for key, (kind, _) in anchors.items() if kind in CLOSEST_KINDS]
    if len(terms) < CLOSEST_MIN_TERMS:
        return Packet()
    holding = set.intersection(*(term_holders(index, key) for key in terms))
    held = [cand for cand in packet.records if cand.pair.pair_id in holding]
    if not CLOSEST_MIN_RECORDS <= len(held) <= CLOSEST_MAX_RECORDS:
        return Packet()
    if sum(1 for cand in held if len(cand.pair.prompt) + len(cand.pair.response) >= CLOSEST_LONG_CHARS) < CLOSEST_LONG_RECORDS:
        return Packet()
    return Packet(records=held)
