"""A case file's event history, read from its records by code and listed by effective step.

A case file ("Use only case file <id>") is an event log rendered as a transcript, a CSV table or a JSON array;
every rendering states the same events. The view lists them one per line, ordered by effective step, so the
deciding model reads one sequence whatever the rendering was. It is found by code and not checked: the records
decide where they differ from it. No value is read for the question here; the chain is the model's to follow.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .protocol import MemoryPair

CASE_FILE_ID_RE = re.compile(r"\bcase file (\w+)", re.IGNORECASE)
CASE_FILE_HEAD_RE = re.compile(r"^\s*Case file (\w+)\b", re.IGNORECASE)
SET_RE = re.compile(r"At effective step (\d+), (add|remove) \"([^\"]+)\" (?:to|from) the \"([^\"]+)\" set of \"([^\"]+)\"")
ASSIGN_TO_FIELD_RE = re.compile(r"The assignment of \"([^\"]+)\" to field \"([^\"]+)\" of \"([^\"]+)\" takes effect at step (\d+)")
BECOMES_RE = re.compile(r"For \"([^\"]+)\", the value of \"([^\"]+)\" becomes \"([^\"]+)\" at effective step (\d+)")
HAS_SET_RE = re.compile(r"Effective at step (\d+), \"([^\"]+)\" has \"([^\"]+)\" set to \"([^\"]+)\"")
CSV_COLUMNS = {"operation", "entity", "field", "value", "effective_step"}
EVENT_LINE_RE = re.compile(r"effective step|takes effect at step|Effective at step|^\s*\{|^[a-z]+,|^\d+,|^entity-|^\s*\|", re.IGNORECASE)
VIEW_MAX_EVENTS = 900

CASE_FILE_VIEW = (
    "The events of case file {name}, read from the records above by code and grouped by the entity changed, each field's changes in step order (not checked; "
    "the records decide where they differ). A scalar field's value at "
    "step S is the assignment with the highest step at or below S, the first-listed one among equal steps; a set at step S holds the "
    "members added at or below S and not removed by a later step at or below S, each member counted once (added, removed and added again by S is in; added then removed by S is out; a set with nobody left is empty and counts as zero). Follow the question's chain one link at a time from "
    "the entity it names, reading each link's value at the step asked, and take each value only from these events.\n{events}"
)
CASE_FILE_VIEW_PARTIAL = "Lines of the records that this listing could not read as events, kept as written:\n{lines}"


@dataclass(frozen=True)
class Event:
    step: int
    entity: str
    field: str
    operation: str
    value: str

    def line(self) -> str:
        if self.operation == "add":
            return f"step {self.step}: {self.entity} . {self.field} += {self.value}"
        if self.operation == "remove":
            return f"step {self.step}: {self.entity} . {self.field} -= {self.value}"
        return f"step {self.step}: {self.entity} . {self.field} = {self.value}"


def case_file_name(message: str) -> str:
    match = CASE_FILE_ID_RE.search(message)
    return match.group(1) if match else ""


def case_file_records(name: str, pairs: list[MemoryPair]) -> list[MemoryPair]:
    return [pair for pair in pairs if (match := CASE_FILE_HEAD_RE.match(pair.prompt)) and match.group(1) == name]


def _csv_events(lines: list[str]) -> tuple[list[Event], set[int]]:
    events: list[Event] = []
    read: set[int] = set()
    columns: list[str] | None = None
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.split(",")]
        if columns is None:
            if len(cells) == 5 and set(cells) == CSV_COLUMNS:
                columns = cells
                read.add(index)
            continue
        if len(cells) != 5:
            continue
        row = dict(zip(columns, cells))
        try:
            events.append(Event(int(row["effective_step"]), row["entity"], row["field"], row["operation"], row["value"]))
            read.add(index)
        except ValueError:
            continue
    return events, read


TABLE_CELL_RE = re.compile(r"<[^>]+>")


def _table_events(lines: list[str]) -> tuple[list[Event], set[int]]:
    """A Markdown table: a header row naming the five columns in any order, a separator row, then one event a row."""
    events: list[Event] = []
    read: set[int] = set()
    columns: list[str] | None = None
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [TABLE_CELL_RE.sub("", cell).strip() for cell in line.strip().strip("|").split("|")]
        if columns is None:
            names = [cell.lower().replace(" ", "_") for cell in cells]
            if len(names) == 5 and set(names) == CSV_COLUMNS:
                columns = names
                read.add(index)
            continue
        if len(cells) != 5 or set(cells) <= {"---", ""}:
            read.add(index)
            continue
        row = dict(zip(columns, cells))
        try:
            events.append(Event(int(row["effective_step"]), row["entity"], row["field"], row["operation"], row["value"]))
            read.add(index)
        except ValueError:
            continue
    return events, read


def _json_events(text: str) -> list[Event]:
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        items = json.loads(text[start : end + 1])
    except ValueError:
        return []
    events: list[Event] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not CSV_COLUMNS <= set(item):
            continue
        try:
            events.append(Event(int(item["effective_step"]), str(item["entity"]), str(item["field"]), str(item["operation"]), str(item["value"])))
        except (TypeError, ValueError):
            continue
    return events


def _sentence_events(lines: list[str]) -> tuple[list[Event], set[int]]:
    events: list[Event] = []
    read: set[int] = set()
    for index, line in enumerate(lines):
        if match := SET_RE.search(line):
            step, operation, member, field, entity = match.groups()
            events.append(Event(int(step), entity, field, operation, member))
        elif match := ASSIGN_TO_FIELD_RE.search(line):
            value, field, entity, step = match.groups()
            events.append(Event(int(step), entity, field, "assign", value))
        elif match := BECOMES_RE.search(line):
            entity, field, value, step = match.groups()
            events.append(Event(int(step), entity, field, "assign", value))
        elif match := HAS_SET_RE.search(line):
            step, entity, field, value = match.groups()
            events.append(Event(int(step), entity, field, "assign", value))
        else:
            continue
        read.add(index)
    return events, read


def parse_record(text: str) -> tuple[list[Event], list[str]]:
    """The events one record states, in document order, and the event-looking lines it could not read."""
    lines = text.split("\n")
    json_events = _json_events(text)
    if json_events:
        return json_events, []
    events, read = _csv_events(lines)
    if not events:
        events, read = _table_events(lines)
    if not events:
        events, read = _sentence_events(lines)
    unread = [line.strip() for index, line in enumerate(lines) if index not in read and EVENT_LINE_RE.search(line) and not CASE_FILE_HEAD_RE.match(line) and "Synthetic operations briefing" not in line]
    return events, unread


def event_view(name: str, records: list[MemoryPair]) -> tuple[str, int, int]:
    """The view text, the number of events listed and the number of event-looking lines left unread."""
    events: list[Event] = []
    unread: list[str] = []
    for pair in records:
        found, missed = parse_record(pair.prompt)
        events += found
        unread += missed
    if not events:
        return "", 0, len(unread)
    # grouped by the entity changed, then by field, each field's changes in step order: one place to look per link of a chain
    by_entity: dict[str, dict[str, list[tuple[int, int, Event]]]] = {}
    for order, event in enumerate(events):
        by_entity.setdefault(event.entity, {}).setdefault(event.field, []).append((event.step, order, event))
    lines: list[str] = []
    for entity in sorted(by_entity):
        lines.append(entity)
        for field in sorted(by_entity[entity]):
            changes = sorted(by_entity[entity][field], key=lambda item: (item[0], item[1]))
            parts = []
            for step, _, event in changes:
                sign = "+=" if event.operation == "add" else "-=" if event.operation == "remove" else "="
                parts.append(f"step {step} {sign} {event.value}")
            lines.append(f"  {field}: " + "; ".join(parts))
    lines = lines[:VIEW_MAX_EVENTS * 2]
    view = CASE_FILE_VIEW.format(name=name, events="\n".join(lines))
    if unread:
        view += "\n\n" + CASE_FILE_VIEW_PARTIAL.format(lines="\n".join(unread[:60]))
    return view, len(lines), len(unread)
