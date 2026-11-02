from __future__ import annotations

import re

from ..packet import Packet
from ..store import CODE_RE

WORKSHEET_HEADER = "Sentences that state a figure, from records grouped by shared identifiers, oldest first. This grouping is mechanical and may include rows unrelated to the message; the records are what count."
WORKSHEET_CUT = "(list cut)"
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
FIGURE_RE = re.compile(r"(?<![A-Za-z0-9-])[$€£]?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z0-9-])")
MAX_GROUPS = 6
MAX_LINES = 60


def link_keys(pair) -> set[str]:
    return {code.upper() for code in CODE_RE.findall(pair.prompt + " " + pair.response)}


def components(packet: Packet) -> list[list[int]]:
    parents = list(range(len(packet.records)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    first_by_key: dict[str, int] = {}
    for index, cand in enumerate(packet.records):
        for key in link_keys(cand.pair):
            if key in first_by_key:
                parents[root(first_by_key[key])] = root(index)
            else:
                first_by_key[key] = index
    grouped: dict[int, list[int]] = {}
    for index in range(len(packet.records)):
        grouped.setdefault(root(index), []).append(index)
    return [sorted(members, key=lambda i: (packet.records[i].pair.timestamp, packet.records[i].pair.pair_id)) for members in grouped.values() if len(members) >= 2]


def sentences(text: str) -> list[str]:
    return [sentence for sentence in SENTENCE_SPLIT.split(" ".join(text.split())) if sentence]


def record_sentences(pair) -> list[str]:
    return sentences(pair.prompt) + sentences(pair.response)


def shared_identifiers(records: list) -> list[str]:
    keys = [link_keys(cand.pair) for cand in records]
    return sorted(set.intersection(*keys) or set.union(*keys))


def group_lines(packet: Packet, members: list[int], labels: dict[str, str]) -> list[str]:
    records = [packet.records[index] for index in members]
    marks = [labels[cand.pair.pair_id] for cand in records]
    figures: list[str] = []
    for cand, mark in zip(records, marks):
        opening = f"[{mark}] {cand.pair.timestamp} — "
        for sentence in record_sentences(cand.pair):
            if FIGURE_RE.search(sentence):
                figures.append(opening + sentence)
    if not figures:
        return []
    return [f"Records {', '.join(marks)} sharing {', '.join(shared_identifiers(records))}"] + figures


def render_worksheet(packet: Packet) -> str:
    groups = components(packet)
    labels = packet.labels()
    blocks: list[list[str]] = []
    used = 0
    cut = len(groups) > MAX_GROUPS
    for members in groups[:MAX_GROUPS]:
        block = group_lines(packet, members, labels)
        if not block:
            continue
        if used + len(block) > MAX_LINES:
            trimmed = block[: MAX_LINES - used]
            if trimmed:
                blocks.append(trimmed)
            cut = True
            break
        blocks.append(block)
        used += len(block)
    if not blocks:
        return ""
    body = "\n\n".join([WORKSHEET_HEADER] + ["\n".join(block) for block in blocks])
    return body + "\n" + WORKSHEET_CUT if cut else body
