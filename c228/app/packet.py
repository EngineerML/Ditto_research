from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from .memory.retrieval import Candidate, UserIndex, identifier_tokens, noted_matter, relevance_band
from .protocol import MemoryPair, handed_out
from .store import CODE_RE

RECORDS_HEADER = "Relevant memory context for this turn:"
QUESTION_HEADER = "Message:"
RECORD_PADDING = 64
MAX_RECORDS = 60
WHO_NOTE_CHARS = 300
WHO_NOTES_MAX = 30
MATTER_OTHERS_CHARS = 6000
MATTER_NOTES_CHARS = 16000
INITIAL_NAME_RE = re.compile(r"\b([A-Z])\.[ \u202f\u00a0]?([A-Z][a-z]{2,})\b")
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
FOLLOW_PER_RECORD = 4
FOLLOW_MAX = 6
FOLLOW_WINDOW_SECONDS = 20 * 60


@dataclass
class Packet:
    records: list[Candidate] = field(default_factory=list)
    focused: bool = False

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


def held_identifier(message: str, ordered: list[Candidate]) -> bool:
    tokens = set(identifier_tokens(message)) | {code.lower() for code in CODE_RE.findall(message)}
    return any(token in (cand.pair.prompt + " " + cand.pair.response).lower() for token in tokens for cand in ordered)


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


def by_matter(packet: Packet, message: str, index: UserIndex) -> Packet:
    """A matter the request names and the user's notes keep, in at most MATTER_NOTES_CHARS: all the notes holding it, then the packet's other records, recalled ones first and then best-ranked, the first of them in whatever its size and further ones while the total stays within MATTER_OTHERS_CHARS."""
    notes = noted_matter(message, index)
    keep = {pair.pair_id for pair in notes}
    held = {cand.pair.pair_id for cand in packet.records}
    holding = [cand for cand in packet.records if cand.pair.pair_id in keep]
    reached = [Candidate(pair=pair, reasons=["matter"]) for pair in notes if pair.pair_id not in held]
    if not notes or sum(record_size(cand) for cand in holding + reached) > MATTER_NOTES_CHARS:
        return packet
    others: list[Candidate] = []
    used = 0
    ranked = sorted((cand for cand in packet.records if cand.pair.pair_id not in keep), key=lambda cand: (not cand.pinned, -cand.score))
    for cand in ranked:
        if not others or used + record_size(cand) <= MATTER_OTHERS_CHARS:
            others.append(cand)
            used += record_size(cand)
    return Packet(records=arc_order(holding + reached + others), focused=packet.focused)


def who_notes(index: UserIndex) -> dict[tuple[str, str], list[MemoryPair]]:
    """The user's short notes that write one person both ways, by initial and surname and by full name, by that initial and surname."""
    held = getattr(index, "_who_notes", None)
    if held is not None:
        return held
    held = {}
    for node in index.nodes.values():
        text = node.pair.prompt
        if len(text) > WHO_NOTE_CHARS or len(node.pair.response) > WHO_NOTE_CHARS:
            continue
        for initial, surname in INITIAL_NAME_RE.findall(text):
            if re.search(rf"\b{initial}[a-z]+ {surname}\b", text):
                held.setdefault((initial, surname), []).append(node.pair)
    index._who_notes = held
    return held


def with_who_notes(packet: Packet, index: UserIndex) -> Packet:
    """A person a packet record's user text writes by initial and surname: the short notes saying who that is go in too, best-ranked records first, up to WHO_NOTES_MAX."""
    known = who_notes(index)
    if not known:
        return packet
    held = {cand.pair.pair_id for cand in packet.records}
    added: list[Candidate] = []
    for cand in sorted(packet.records, key=lambda cand: -cand.score):
        for name in INITIAL_NAME_RE.findall(cand.pair.prompt):
            for pair in known.get(name, []):
                if pair.pair_id not in held and len(added) < WHO_NOTES_MAX:
                    held.add(pair.pair_id)
                    added.append(Candidate(pair=pair, reasons=["who"]))
    return Packet(records=packet.records + added, focused=packet.focused) if added else packet


def build_packet(ordered: list[Candidate], anchored: bool, budget: int, message: str, index: UserIndex, fused: list[str] | None = None, meaning_records: int = 0, meaning_chars: int = 0, ceiling: int = 0) -> Packet:
    packet = linked_packet(ordered, anchored, budget, message, index)
    if not fused:
        return by_date(with_who_notes(packet, index))
    focus = identifier_focus(message, ordered)
    if anchored and not focus:
        packet = by_meaning(packet, fused, index, meaning_records, min(meaning_chars, ceiling - packet.chars))
    packet = by_seat(packet, fused)
    return by_date(with_who_notes(by_matter(packet, message, index) if not focus else packet, index))


def by_date(packet: Packet) -> Packet:
    """A packet without a focus (no identifier, thread or lead) is listed oldest first, whatever the relevance bands admitted, so that a record that changes, drops or brings back something comes after the records it changes; a focused packet keeps its arc order."""
    if packet.focused:
        return packet
    return Packet(records=sorted(packet.records, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id)), focused=False)


def linked_packet(ordered: list[Candidate], anchored: bool, budget: int, message: str, index: UserIndex) -> Packet:
    packet = assemble(ordered, anchored, budget - LINK_RESERVE, message)
    reached = link_hop(index, packet.records, budget)
    if not reached:
        return assemble(ordered, anchored, budget, message)
    return Packet(records=packet.records + reached, focused=packet.focused)


def assemble(ordered: list[Candidate], anchored: bool, budget: int, message: str) -> Packet:
    if message:
        focused = identifier_focus(message, ordered)
        if focused:
            held = {cand.pair.pair_id for cand in focused}
            kept = admit([cand for cand in ordered if cand.pinned and cand.pair.pair_id not in held], budget, focused)
            return Packet(records=sorted(kept, key=lambda cand: (cand.pair.timestamp, cand.pair.pair_id)), focused=True)
    thread = leading_thread(ordered)
    if thread:
        return Packet(records=arc_order(value_closure(ordered, thread, budget)), focused=True)
    lead = anchored_thread(ordered)
    if lead:
        names = {cand.pair.pair_id for cand in lead}
        floor = DUAL_SHARE * ordered[0].score
        held = admit([cand for cand in ordered if cand.pair.pair_id not in names and cand.score >= floor], budget, lead)
        return Packet(records=arc_order(value_closure(ordered, held, budget)), focused=True)
    if not anchored:
        ordered = ordered[:UNANCHORED_MAX_RECORDS]
    admitted = admit(ordered, budget)
    top = max((cand.score for cand in admitted), default=0.0)
    admitted.sort(key=lambda cand: (relevance_band(cand.score, top), cand.pair.timestamp, cand.pair.pair_id))
    return Packet(records=arc_order(admitted))


def render_records(packet: Packet, labels: dict[str, str] | None = None) -> str:
    marks = labels if labels is not None else packet.labels()
    lines: list[str] = []
    for cand in packet.records:
        pair = cand.pair
        lines.append(f"[{marks[pair.pair_id]}]" + (f" same conversation as {marks[cand.continues]}" if cand.continues in marks else "") + (f" pair_id={pair.pair_id}" if handed_out(pair.pair_id) else "") + f" time={pair.timestamp}")
        lines.append(f"User: {pair.prompt.strip()}")
        if pair.response.strip():
            lines.append(f"Assistant: {pair.response.strip()}")
        lines.append("")
    return "\n".join(lines).strip()


def name_ties(cand: Candidate, ties: dict[str, tuple[str, list[str]]] | None, marks: dict[str, str] | None = None) -> list[dict[str, str]]:
    """The called names (M48) this record writes as a whole word while not writing the name they are tied to: each with that name and, when a record stating the tie is in the packet, that record's mark."""
    if not ties:
        return []
    text = cand.pair.prompt + "\n" + cand.pair.response
    out: list[dict[str, str]] = []
    for alias, (full, stated) in ties.items():
        if re.search(r"\b" + re.escape(full) + r"\b", text) or not re.search(r"\b" + re.escape(alias) + r"\b", text):
            continue
        tie = {"name": alias, "sameAs": full}
        mark = next((marks[pid] for pid in stated if marks and pid in marks), "")
        if mark:
            tie["tiedBy"] = mark
        out.append(tie)
    return out


def weave_ties(packet: Packet, ties: dict[str, tuple[str, list[str]]] | None) -> int:
    """Seats each record that carries a name tie right after the last packet record that writes the name it is tied to, in their order; records are moved, never changed."""
    if not ties or not packet.records:
        return 0
    moved = 0
    for alias, (full, stated) in ties.items():
        one = {alias: (full, stated)}
        movers = [cand for cand in packet.records if name_ties(cand, one)]
        rest = [cand for cand in packet.records if cand not in movers]
        pattern = re.compile(r"\b" + re.escape(full) + r"\b")
        last = max((position for position, cand in enumerate(rest) if pattern.search(cand.pair.prompt + "\n" + cand.pair.response)), default=None)
        if not movers or last is None:
            continue
        packet.records[:] = rest[: last + 1] + movers + rest[last + 1 :]
        moved += len(movers)
    return moved


def memory_entry(cand: Candidate, mark: str, continues: str = "", ties: dict[str, tuple[str, list[str]]] | None = None, marks: dict[str, str] | None = None, changed: bool = False) -> str:
    pair = cand.pair
    entry = {"mark": mark}
    if changed:
        entry["rewrittenByUser"] = True
    if continues:
        entry["sameConversationAs"] = continues
    tied = name_ties(cand, ties, marks)
    if tied:
        entry["nameTies"] = tied
    if handed_out(pair.pair_id):
        entry["pairID"] = pair.pair_id
    entry["timestamp"] = pair.timestamp
    entry["user"] = pair.prompt.strip()
    if pair.response.strip():
        entry["ditto"] = pair.response.strip()
    return json.dumps(entry, ensure_ascii=False)


def memory_context(packet: Packet, labels: dict[str, str] | None = None, ties: dict[str, tuple[str, list[str]]] | None = None, changed: frozenset[str] = frozenset()) -> str:
    marks = labels if labels is not None else packet.labels()
    entries = ",\n".join(memory_entry(cand, marks[cand.pair.pair_id], marks.get(cand.continues, ""), ties, marks, cand.pair.pair_id in changed) for cand in packet.records)
    return RECORDS_HEADER + '\n{"longTerm": {"memories": [\n' + entries + "\n]}}"


def compose(packet: Packet, message: str, precursor: str = "", labels: dict[str, str] | None = None, ties: dict[str, tuple[str, list[str]]] | None = None, changed: frozenset[str] = frozenset()) -> str:
    if not packet.records:
        return message
    parts = [memory_context(packet, labels, ties, changed), ""]
    if precursor:
        parts += [precursor, ""]
    parts += [QUESTION_HEADER, message]
    return "\n".join(parts)


def _seconds(timestamp: str) -> float | None:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def session_followups(packet: Packet, index: UserIndex | None) -> list[Candidate]:
    """Later turns of the conversation an anchored packet record belongs to (same session id, within 20 minutes of it, up to 4 a record and 6 a packet), as candidates that carry the record they continue. A later turn of a conversation often changes or adds to what the first turn said without naming it again; the session id is the only tie between them."""
    if index is None or not packet.records:
        return []
    sessions: dict[str, list[MemoryPair]] = {}
    for node in index.nodes.values():
        if node.pair.session_id:
            sessions.setdefault(node.pair.session_id, []).append(node.pair)
    held = {cand.pair.pair_id for cand in packet.records}
    added: list[Candidate] = []
    for cand in sorted((cand for cand in packet.records if cand.anchored), key=lambda cand: -cand.score):
        turns = sessions.get(cand.pair.session_id)
        start = _seconds(cand.pair.timestamp)
        if not turns or start is None:
            continue
        later = sorted((pair for pair in turns if pair.timestamp > cand.pair.timestamp), key=lambda pair: (pair.timestamp, pair.pair_id))
        for pair in later[:FOLLOW_PER_RECORD]:
            at = _seconds(pair.timestamp)
            if at is None or at - start > FOLLOW_WINDOW_SECONDS:
                break
            if pair.pair_id in held:
                continue
            held.add(pair.pair_id)
            added.append(Candidate(pair=pair, reasons=["same conversation, later turn"], continues=cand.pair.pair_id))
            if len(added) >= FOLLOW_MAX:
                return added
    return added


EMPLOYER_RE = re.compile(r"\b(?:used to work at|work(?:s|ed)? at|moved to|joined|now at|at) ([A-Z][\w&'-]*(?: [A-Z][\w&'-]*){0,3})")
EMPLOYER_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
EMPLOYER_MAX_RECORDS = 6
EMPLOYER_RECORD_CHARS = 400


def employer_records(packet: Packet, index: UserIndex | None) -> int:
    """A contact question: a past address is filed under the employer of the time, not the person's name, so the short records that hold an address and name an employer a packet record gives for someone (used to work at, moved to, joined, at) are seated after the packet, oldest first, up to 6; found by code, read by the model."""
    if index is None or not packet.records:
        return 0
    employers = {match.group(1).lower() for cand in packet.records for match in EMPLOYER_RE.finditer(cand.pair.prompt)}
    if not employers:
        return 0
    held = {cand.pair.pair_id for cand in packet.records}
    added: list[Candidate] = []
    for node in sorted(index.nodes.values(), key=lambda node: (node.pair.timestamp, node.pair.pair_id)):
        pair = node.pair
        if pair.pair_id in held or len(pair.prompt) > EMPLOYER_RECORD_CHARS or not EMPLOYER_EMAIL_RE.search(pair.prompt):
            continue
        low = pair.prompt.lower()
        if any(employer in low for employer in employers):
            held.add(pair.pair_id)
            added.append(Candidate(pair=pair, reasons=["holds an address and names an employer a packet record gives"]))
            if len(added) >= EMPLOYER_MAX_RECORDS:
                break
    packet.records.extend(added)
    return len(added)


def weave_followups(packet: Packet, index: UserIndex | None) -> int:
    """Seats each follow-up turn right after the record it continues; the record text is unchanged and the tie is shown as `sameConversationAs`."""
    added = session_followups(packet, index)
    after: dict[str, list[Candidate]] = {}
    for cand in added:
        after.setdefault(cand.continues, []).append(cand)
    if after:
        packet.records[:] = [seat for cand in packet.records for seat in (cand, *after.get(cand.pair.pair_id, ()))]
    return len(added)
