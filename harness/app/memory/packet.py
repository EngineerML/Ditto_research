from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.memory.retrieval import Candidate, UserIndex, identifier_tokens, relevance_band
from app.protocol import handed_out
from app.memory.store import CODE_RE

RECORDS_HEADER = "Relevant memory context for this turn:"
QUESTION_HEADER = "Message:"
RECORD_PADDING = 64
MAX_RECORDS = 60
UNANCHORED_MAX_RECORDS = 3
THREAD_POOL = 40
THREAD_MIN_RECORDS = 3
THREAD_MAX_RECORDS = 12
THREAD_TAIL = 2
THREAD_LEAD = 5
THREAD_RATIO = 2.0
DUAL_ANCHORED = 2
DUAL_SHARE = 0.2
CLOSURE_MAX_RECORDS = 8
CLOSURE_BAND_SHARE = 0.45
LINK_MAX_CHARS = 700
LINK_PER_HOP = 10
LINK_HOPS = 2
LINK_RESERVE = 4000


@dataclass
class Packet:
    records: list[Candidate] = field(default_factory=list)
    focused: bool = False
    widened: int = 0

    def labels(self) -> dict[str, str]:
        return {cand.pair.pair_id: f"M{position}" for position, cand in enumerate(self.records, start=1)}

    @property
    def chars(self) -> int:
        return sum(record_size(cand) for cand in self.records)

    def __len__(self) -> int:
        return len(self.records)


def record_size(cand: Candidate) -> int:
    return len(cand.pair.prompt) + len(cand.pair.response) + RECORD_PADDING


def codes_of(cand: Candidate) -> set[str]:
    return set(CODE_RE.findall(cand.pair.prompt + " " + cand.pair.response))


def code_components(records: list[Candidate]) -> list[list[Candidate]]:
    parent = {cand.pair.pair_id: cand.pair.pair_id for cand in records}

    def root(pair_id: str) -> str:
        while parent[pair_id] != pair_id:
            parent[pair_id] = parent[parent[pair_id]]
            pair_id = parent[pair_id]
        return pair_id

    holder: dict[str, str] = {}
    for cand in records:
        for code in sorted(codes_of(cand)):
            if code in holder:
                parent[root(cand.pair.pair_id)] = root(holder[code])
            else:
                holder[code] = cand.pair.pair_id
    grouped: dict[str, list[Candidate]] = {}
    for cand in records:
        grouped.setdefault(root(cand.pair.pair_id), []).append(cand)
    return list(grouped.values())


def identifier_focus(message: str, ordered: list[Candidate]) -> list[Candidate]:
    for token in identifier_tokens(message):
        carrying = [cand for cand in ordered if token in (cand.pair.prompt + " " + cand.pair.response).lower()]
        if len(carrying) >= THREAD_MIN_RECORDS:
            return sorted(carrying, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id))
    return []


def arc_order(admitted: list[Candidate]) -> list[Candidate]:
    seat = {cand.pair.pair_id: index for index, cand in enumerate(admitted)}
    blocks: list[tuple[int, list[Candidate]]] = []
    for members in code_components(admitted):
        members = sorted(members, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id))
        blocks.append((min(seat[cand.pair.pair_id] for cand in members), members))
    blocks.sort(key=lambda block: block[0])
    return [cand for _, members in blocks for cand in members]


def strongest_group(ordered: list[Candidate]) -> list[Candidate]:
    if not ordered:
        return []
    groups = code_components(ordered[:THREAD_POOL])
    best = max(groups, key=lambda members: sum(cand.score for cand in members))
    if not THREAD_MIN_RECORDS <= len(best) <= THREAD_MAX_RECORDS:
        return []
    return sorted(best, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id))


def leading_thread(ordered: list[Candidate]) -> list[Candidate]:
    thread = strongest_group(ordered)
    if not thread:
        return []
    names = {cand.pair.pair_id for cand in thread}
    leads = ordered[0].pair.pair_id in names or sum(cand.score for cand in thread) >= THREAD_RATIO * max(cand.score for cand in ordered[:THREAD_LEAD])
    if not leads:
        return []
    return thread + [cand for cand in ordered if cand.pair.pair_id not in names][:THREAD_TAIL]


def anchored_thread(ordered: list[Candidate]) -> list[Candidate]:
    thread = strongest_group(ordered)
    if sum(1 for cand in thread if cand.anchored) < DUAL_ANCHORED:
        return []
    return thread


def value_closure(ordered: list[Candidate], held: list[Candidate], budget: int) -> list[Candidate]:
    shared = set().union(*(cand.keys for cand in held)) if held else set()
    names = {cand.pair.pair_id for cand in held}
    top = max((cand.score for cand in ordered), default=0.0)
    asked = [cand for cand in ordered if cand.pair.pair_id not in names and cand.pinned]
    linked = [cand for cand in ordered if cand.pair.pair_id not in names and not cand.pinned and cand.keys & shared][:CLOSURE_MAX_RECORDS]
    band = [cand for cand in ordered if cand.pair.pair_id not in names and not cand.pinned and cand.score >= CLOSURE_BAND_SHARE * top]
    reached = {cand.pair.pair_id for cand in asked + linked}
    return admit(asked + linked + [cand for cand in band if cand.pair.pair_id not in reached], budget, held)


def link_hop(index: UserIndex, held: list[Candidate], budget: int) -> list[Candidate]:
    holding = {cand.pair.pair_id for cand in held}
    anchored = {cand.pair.pair_id for cand in held if cand.anchored}
    if anchored:
        anchored |= index.linked(sorted(anchored), holding)
    seen = set(holding)
    frontier = sorted(anchored) or sorted(holding)
    carried: dict[str, float] = {}
    for _ in range(LINK_HOPS):
        step = index.neighbours(frontier, seen, LINK_MAX_CHARS, LINK_PER_HOP)
        if not step:
            break
        seen.update(step)
        carried.update(step)
        frontier = list(step)
    used = sum(record_size(cand) for cand in held)
    reached: list[Candidate] = []
    for pair_id in sorted(carried, key=lambda pid: (-carried[pid], index.nodes[pid].size, pid)):
        node = index.nodes[pair_id]
        cand = Candidate(pair=node.pair, reasons=["link"], keys=frozenset(node.values))
        if used + record_size(cand) > budget:
            continue
        used += record_size(cand)
        reached.append(cand)
    return reached


def admit(ordered: list[Candidate], budget: int, admitted: list[Candidate] | None = None) -> list[Candidate]:
    admitted = list(admitted or [])
    used = sum(record_size(cand) for cand in admitted)
    for cand in ordered:
        if len(admitted) >= MAX_RECORDS:
            break
        size = record_size(cand)
        if used + size > budget and admitted:
            continue
        admitted.append(cand)
        used += size
    return admitted


def by_meaning(packet: Packet, fused: list[str], index: UserIndex, max_records: int, max_chars: int) -> Packet:
    held = {cand.pair.pair_id for cand in packet.records}
    added: list[Candidate] = []
    used = 0
    for pair_id in fused:
        if len(added) >= max_records:
            break
        node = index.nodes.get(pair_id)
        if node is None or pair_id in held:
            continue
        cand = Candidate(pair=node.pair, reasons=["meaning"], keys=frozenset(node.values))
        if used + record_size(cand) > max_chars:
            continue
        added.append(cand)
        used += record_size(cand)
    return Packet(records=packet.records + added, focused=packet.focused)


def by_seat(packet: Packet, fused: list[str]) -> Packet:
    seat = {pair_id: position for position, pair_id in enumerate(fused)}
    ranked = sorted(packet.records, key=lambda cand: seat.get(cand.pair.pair_id, len(seat)))
    return Packet(records=arc_order(ranked), focused=packet.focused)


def build_packet(ordered: list[Candidate], anchored: bool, budget: int, arc: bool = False, thread_first: bool = False, message: str = "", closure: bool = False, index: UserIndex | None = None, fused: list[str] | None = None, meaning_records: int = 0, meaning_chars: int = 0, ceiling: int = 0, meaning_order: bool = False) -> Packet:
    if index is not None and fused:
        packet = build_packet(ordered, anchored, budget, arc, thread_first, message, closure, index)
        if meaning_records > 0 and anchored and not identifier_focus(message, ordered):
            room = min(meaning_chars, ceiling - packet.chars) if ceiling > 0 else meaning_chars
            packet = by_meaning(packet, fused, index, meaning_records, room)
        return by_seat(packet, fused) if meaning_order else packet
    if index is None:
        return assemble(ordered, anchored, budget, arc, thread_first, message, closure)
    packet = assemble(ordered, anchored, budget - LINK_RESERVE, arc, thread_first, message, closure)
    reached = link_hop(index, packet.records, budget)
    if not reached:
        return assemble(ordered, anchored, budget, arc, thread_first, message, closure)
    return Packet(records=packet.records + reached, focused=packet.focused)


def assemble(ordered: list[Candidate], anchored: bool, budget: int, arc: bool = False, thread_first: bool = False, message: str = "", closure: bool = False) -> Packet:
    if message:
        focused = identifier_focus(message, ordered)
        if focused:
            held = {cand.pair.pair_id for cand in focused}
            kept = admit([cand for cand in ordered if cand.pinned and cand.pair.pair_id not in held], budget, focused)
            return Packet(records=sorted(kept, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id)), focused=True)
    if thread_first:
        thread = leading_thread(ordered)
        if thread:
            if not closure:
                return Packet(records=thread, focused=True)
            widened = value_closure(ordered, thread, budget)
            return Packet(records=arc_order(widened) if arc else widened, focused=True)
        lead = anchored_thread(ordered)
        if lead:
            names = {cand.pair.pair_id for cand in lead}
            floor = DUAL_SHARE * ordered[0].score
            held = admit([cand for cand in ordered if cand.pair.pair_id not in names and cand.score >= floor], budget, lead)
            if not closure:
                return Packet(records=held, focused=True)
            widened = value_closure(ordered, held, budget)
            return Packet(records=arc_order(widened) if arc else widened, focused=True)
    if not anchored:
        ordered = ordered[:UNANCHORED_MAX_RECORDS]
    admitted = admit(ordered, budget)
    top = max((cand.score for cand in admitted), default=0.0)
    admitted.sort(key=lambda cand: (relevance_band(cand.score, top), cand.pair.timestamp, cand.pair.pair_id))
    return Packet(records=arc_order(admitted) if arc else admitted)


RRF_K = 60
RRF_DEPTH = 80


def fused_rank(orders: list[tuple[list[str], float]]) -> list[str]:
    """Weighted reciprocal-rank fusion of several orders of record ids, best first."""
    score: dict[str, float] = {}
    for order, weight in orders:
        for rank, pair_id in enumerate(order[:RRF_DEPTH], start=1):
            score[pair_id] = score.get(pair_id, 0.0) + weight / (RRF_K + rank)
    return sorted(score, key=lambda pair_id: -score[pair_id])


def swap_in(packet: Packet, better: list[str], pairs_by_id: dict, top: int) -> Packet:
    """Bring the `top` best records of `better` into the packet without growing it.

    Each record brought in replaces the packet's records that rank lowest in `better`, until it fits in the
    packet's own size, so the prompt keeps the length the base budget gave it.
    """
    budget = packet.chars
    rank = {pair_id: position for position, pair_id in enumerate(better)}
    head = [pair_id for pair_id in better[:top] if pair_id in pairs_by_id]
    kept = list(packet.records)
    for pair_id in head:
        if any(cand.pair.pair_id == pair_id for cand in kept):
            continue
        incoming = Candidate(pair=pairs_by_id[pair_id], reasons=["swap"])
        used = sum(record_size(cand) for cand in kept)
        victims = sorted((cand for cand in kept if cand.pair.pair_id not in head), key=lambda cand: -rank.get(cand.pair.pair_id, 10**6))
        while used + record_size(incoming) > budget and victims:
            out = victims.pop(0)
            kept.remove(out)
            used -= record_size(out)
        if used + record_size(incoming) <= budget:
            kept.append(incoming)
    return Packet(records=kept, focused=packet.focused, widened=packet.widened)


def refill(packet: Packet, better: list[str], pairs_by_id: dict, max_new_chars: int = 0) -> Packet:
    """Refill the packet's own size from the fused order, best first.

    The kept records of the base packet stay in their places (so its arc and date order holds), and the records it
    lacked follow in fused order. The packet never grows past its own size. A record the base packet did not hold is
    brought in only when it is shorter than `max_new_chars` (0: any size), so a refill never turns a packet into a
    long-record one that starts extra search passes.
    """
    budget = packet.chars
    base = {cand.pair.pair_id for cand in packet.records}
    chosen: list[str] = []
    used = 0
    for pair_id in better:
        pair = pairs_by_id.get(pair_id)
        if pair is None:
            continue
        size = record_size(Candidate(pair=pair))
        if used + size > budget:
            continue
        if max_new_chars and pair_id not in base and len(pair.prompt) + len(pair.response) >= max_new_chars:
            continue
        chosen.append(pair_id)
        used += size
    picked = set(chosen)
    kept = [cand for cand in packet.records if cand.pair.pair_id in picked]
    held = {cand.pair.pair_id for cand in kept}
    added = [Candidate(pair=pairs_by_id[pair_id], reasons=["refill"]) for pair_id in chosen if pair_id not in held]
    return Packet(records=kept + added, focused=packet.focused, widened=packet.widened)


def widen(packet: Packet, extra: list[Candidate], budget: int) -> Packet:
    """Append records found by meaning or by full-text search that the packet lacks, within budget.

    The packet's own records are never dropped or reordered, so its marks stay as they were.
    `widened` counts the characters added, so a long-packet rule can still read the base size.
    """
    held = {cand.pair.pair_id for cand in packet.records}
    used = packet.chars
    added: list[Candidate] = []
    for cand in extra:
        if cand.pair.pair_id in held or len(packet.records) + len(added) >= MAX_RECORDS:
            continue
        size = record_size(cand)
        if used + size > budget:
            continue
        held.add(cand.pair.pair_id)
        added.append(cand)
        used += size
    if not added:
        return packet
    return Packet(records=packet.records + added, focused=packet.focused, widened=packet.widened + sum(record_size(c) for c in added))


def render_records(packet: Packet, labels: dict[str, str] | None = None) -> str:
    marks = labels if labels is not None else packet.labels()
    lines: list[str] = []
    for cand in packet.records:
        pair = cand.pair
        lines.append(f"[{marks[pair.pair_id]}]" + (f" pair_id={pair.pair_id}" if handed_out(pair.pair_id) else "") + f" time={pair.timestamp}")
        lines.append(f"User: {pair.prompt.strip()}")
        if pair.response.strip():
            lines.append(f"Assistant: {pair.response.strip()}")
        lines.append("")
    return "\n".join(lines).strip()


def memory_entry(cand: Candidate, mark: str) -> str:
    pair = cand.pair
    entry = {"mark": mark}
    if handed_out(pair.pair_id):
        entry["pairID"] = pair.pair_id
    entry["timestamp"] = pair.timestamp
    entry["user"] = pair.prompt.strip()
    if pair.response.strip():
        entry["ditto"] = pair.response.strip()
    return json.dumps(entry, ensure_ascii=False)


def memory_context(packet: Packet, labels: dict[str, str] | None = None) -> str:
    marks = labels if labels is not None else packet.labels()
    entries = ",\n".join(memory_entry(cand, marks[cand.pair.pair_id]) for cand in packet.records)
    return RECORDS_HEADER + '\n{"longTerm": {"memories": [\n' + entries + "\n]}}"


def compose(packet: Packet, message: str, precursor: str = "", labels: dict[str, str] | None = None) -> str:
    if not packet.records:
        return message
    parts = [memory_context(packet, labels), ""]
    if precursor:
        parts += [precursor, ""]
    parts += [QUESTION_HEADER, message]
    return "\n".join(parts)
