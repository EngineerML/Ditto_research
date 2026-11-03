from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

FIND_TOOL_NAME = "find_in_records"
MAX_FIND_TEXTS = 4
MAX_TEXT_CHARS = 200
MAX_SHOWN_PARTS = 30
MAX_RESULT_CHARS = 12000
PARAGRAPH_MAX_CHARS = 1200
TABLE_MIN_LINES = 3
TABLE_MAX_HEADER_CHARS = 60
JSON_OPENERS = "[{"
DASHES = "‐‑‒–—―−﹘﹣－"
MARKDOWN_RULE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
SPACE_RUN = re.compile(r"\s+")

FIND_TOOL = {
    "type": "function",
    "function": {
        "name": FIND_TOOL_NAME,
        "description": "Looks up texts in the records attached to this message. Each text is looked up on its own: every part of the records that holds it comes back whole, under the mark of its record and in the order the records show them - a table row as an object of its column names and cells, a JSON object, or a paragraph. Letter case and the kind of dash or space do not matter. Use it to follow an identifier or a name through long records, one lookup after another, instead of reading them end to end.",
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {"type": "array", "items": {"type": "string"}, "description": "One to four texts to look up, for example identifiers or names from the message or from parts found earlier."},
            },
            "required": ["texts"],
        },
    },
}
ORDERED_FIND_TOOL = {
    "type": "function",
    "function": {
        "name": FIND_TOOL_NAME,
        "description": "Looks up texts in the records attached to this message. Each text is looked up on its own: every part of the records that holds it comes back whole, under the mark of its record and in the order the records show them, or, with order_by, in the order of the whole number each part gives for the word or column you name, from smallest to largest - a table row as an object of its column names and cells, a JSON object, or a paragraph. Letter case and the kind of dash or space do not matter. Use it to follow an identifier or a name through long records, one lookup after another, instead of reading them end to end.",
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {"type": "array", "items": {"type": "string"}, "description": "One to four texts to look up, for example identifiers or names from the message or from parts found earlier."},
                "order_by": {"type": "string", "description": "Optional: a word or column name. The parts found are then listed in the order of the whole number that comes right after that word in each part, or in that column, from smallest to largest; parts without one come last."},
            },
            "required": ["texts"],
        },
    },
}
NO_TEXT = "find_in_records needs at least one non-empty text in texts."
NO_RECORDS = "No records are attached to this message, so there is nothing to look up."
FOUND_HEADER = "{text} is in {found} part{plural} of the attached records:"
NOTHING_FOUND = "{text} is in no part of the attached records ({marks}). A shorter text, such as a single identifier or name, may find what you are after."
CUT_NOTE = "{hidden} more part{plural} with {text} are not shown; look it up on its own or with a longer text."
UNSHOWN_TEXT = "{text} was not looked up in this reply because the reply is full; look it up again."
ORDER_NOTE = "Listed in the order of the number after {word}, from smallest to largest; parts without one come last."
MAX_ORDER_CHARS = 60
WHOLE_NUMBER = re.compile(r"-?\d+")


@dataclass(frozen=True)
class Part:
    mark: str
    text: str


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join("-" if char in DASHES else char for char in text)
    return SPACE_RUN.sub(" ", text).strip().casefold()


def leaf_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        nested = [item for item in value.values() if isinstance(item, (dict, list))]
        if not nested:
            return [value]
        found: list[dict[str, Any]] = []
        for item in nested:
            found.extend(leaf_objects(item))
        scalars = {key: item for key, item in value.items() if not isinstance(item, (dict, list))}
        return ([scalars] if scalars else []) + found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(leaf_objects(item))
        return found
    return []


def json_block(text: str, start: int) -> tuple[list[str], int] | None:
    try:
        value, end = json.JSONDecoder().raw_decode(text, start)
    except ValueError:
        return None
    line_end = text.find("\n", end)
    rest = text[end:] if line_end < 0 else text[end:line_end]
    objects = leaf_objects(value) if isinstance(value, (dict, list)) else []
    if not objects or rest.strip():
        return None
    return [json.dumps(item, ensure_ascii=False) for item in objects], end


def csv_fields(line: str) -> list[str] | None:
    if "," not in line:
        return None
    try:
        rows = list(csv.reader([line]))
    except csv.Error:
        return None
    return rows[0] if len(rows) == 1 and len(rows[0]) >= 2 else None


def table_row(header: list[str], cells: list[str]) -> str:
    return json.dumps(dict(zip(header, cells)), ensure_ascii=False)


def usable_header(cells: list[str]) -> bool:
    return all(cell.strip() and len(cell.strip()) <= TABLE_MAX_HEADER_CHARS for cell in cells) and len({cell.strip() for cell in cells}) == len(cells)


def markdown_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def csv_table(lines: list[str], start: int) -> tuple[list[str], int] | None:
    header = csv_fields(lines[start])
    if header is None or not usable_header(header):
        return None
    end = start + 1
    rows: list[list[str]] = []
    while end < len(lines):
        cells = csv_fields(lines[end]) if lines[end].strip() else None
        if cells is None or len(cells) != len(header):
            break
        rows.append(cells)
        end += 1
    if end - start < TABLE_MIN_LINES:
        return None
    return [table_row([cell.strip() for cell in header], row) for row in rows], end


def markdown_table(lines: list[str], start: int) -> tuple[list[str], int] | None:
    if start + 1 >= len(lines) or not lines[start].strip().startswith("|") or not MARKDOWN_RULE.match(lines[start + 1].strip()):
        return None
    header = markdown_cells(lines[start])
    if not usable_header(header):
        return None
    end = start + 2
    rows: list[str] = []
    while end < len(lines) and lines[end].strip().startswith("|"):
        cells = markdown_cells(lines[end])
        rows.append(table_row(header, cells) if len(cells) == len(header) else lines[end].strip())
        end += 1
    return rows, end


def paragraph_parts(lines: list[str]) -> list[str]:
    text = "\n".join(lines).strip()
    if not text:
        return []
    if len(text) <= PARAGRAPH_MAX_CHARS:
        return [text]
    return [line.strip() for line in lines if line.strip()]


def split_parts(text: str) -> list[str]:
    lines = text.split("\n")
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line) + 1
    parts: list[str] = []
    pending: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        block: tuple[list[str], int] | None = None
        if stripped[:1] in JSON_OPENERS and stripped[:1]:
            decoded = json_block(text, offsets[index] + len(line) - len(line.lstrip()))
            if decoded is not None:
                items, end_char = decoded
                end_line = index
                while end_line < len(lines) and offsets[end_line] < end_char:
                    end_line += 1
                block = (items, end_line)
        if block is None and stripped.startswith("|"):
            block = markdown_table(lines, index)
        if block is None and stripped:
            block = csv_table(lines, index)
        if block is not None:
            parts.extend(paragraph_parts(pending))
            pending = []
            parts.extend(block[0])
            index = max(block[1], index + 1)
            continue
        if not stripped:
            parts.extend(paragraph_parts(pending))
            pending = []
        else:
            pending.append(line)
        index += 1
    parts.extend(paragraph_parts(pending))
    return parts


def record_parts(mark: str, prompt: str, response: str) -> list[Part]:
    found = [Part(mark, part) for part in split_parts(prompt)]
    if response.strip():
        found.extend(Part(mark, part) for part in split_parts(response))
    return found


def wanted_texts(args: dict[str, Any]) -> list[str]:
    raw = args.get("texts")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    texts: list[str] = []
    for item in raw:
        if isinstance(item, (str, int, float)) and not isinstance(item, bool):
            value = str(item).strip()[:MAX_TEXT_CHARS]
            if value and value not in texts:
                texts.append(value)
    return texts[:MAX_FIND_TEXTS]


def order_word(args: dict[str, Any]) -> str:
    raw = args.get("order_by")
    if not isinstance(raw, (str, int)) or isinstance(raw, bool):
        return ""
    return key_words(str(raw))[:MAX_ORDER_CHARS]


def key_words(text: str) -> str:
    return fold(text.replace("_", " "))


def named_in(name: str, word: str) -> bool:
    return f" {word} " in f" {name} "


def number_after(text: str, word: str) -> int | None:
    words = [word] + ([word.split()[-1]] if " " in word else [])
    try:
        value = json.loads(text)
    except ValueError:
        value = None
    for each in words:
        if isinstance(value, dict):
            for key, cell in value.items():
                if named_in(key_words(str(key)), each):
                    found = WHOLE_NUMBER.search(fold(str(cell)))
                    if found:
                        return int(found.group(0))
        found = re.search(r"(?<!\w)" + re.escape(each) + r"(?!\w)\W{0,3}(-?\d+)", key_words(text))
        if found:
            return int(found.group(1))
    return None


def rank(item: tuple[int | None, int, Part]) -> tuple[bool, int, int]:
    value, position, _ = item
    return value is None, value or 0, position


def ordered(parts: list[Part], word: str) -> list[Part]:
    if not word:
        return parts
    keyed = [(number_after(part.text, word), index, part) for index, part in enumerate(parts)]
    return [part for _, _, part in sorted(keyed, key=rank)]


def plural(amount: int) -> str:
    return "" if amount == 1 else "s"


class RecordFinder:
    def __init__(self, records: list[tuple[str, str, str]], ordering: bool = False) -> None:
        self.ordering = ordering
        self.tool = ORDERED_FIND_TOOL if ordering else FIND_TOOL
        self.marks = [mark for mark, _, _ in records]
        self.parts: list[Part] = []
        for mark, prompt, response in records:
            self.parts.extend(record_parts(mark, prompt, response))
        self.folded = [fold(part.text) for part in self.parts]

    def find(self, text: str) -> list[Part]:
        needle = fold(text)
        return [part for part, haystack in zip(self.parts, self.folded) if needle in haystack]

    def run(self, args: dict[str, Any]) -> str:
        texts = wanted_texts(args)
        if not texts:
            return NO_TEXT
        if not self.marks:
            return NO_RECORDS
        word = order_word(args) if self.ordering else ""
        blocks: list[str] = [ORDER_NOTE.format(word=json.dumps(word, ensure_ascii=False))] if word else []
        size = 0
        for text in texts:
            label = json.dumps(text, ensure_ascii=False)
            if size >= MAX_RESULT_CHARS:
                blocks.append(UNSHOWN_TEXT.format(text=label))
                continue
            hits = ordered(self.find(text), word)
            if not hits:
                block = [NOTHING_FOUND.format(text=label, marks=", ".join(self.marks))]
            else:
                block = [FOUND_HEADER.format(text=label, found=len(hits), plural=plural(len(hits)))]
                shown = 0
                for part in hits:
                    line = f"[{part.mark}] {part.text}"
                    if shown >= MAX_SHOWN_PARTS or (shown and size + len(line) + 1 > MAX_RESULT_CHARS):
                        break
                    block.append(line)
                    size += len(line) + 1
                    shown += 1
                if len(hits) > shown:
                    block.append(CUT_NOTE.format(hidden=len(hits) - shown, plural=plural(len(hits) - shown), text=label))
            size += len(block[0]) + 1
            blocks.append("\n".join(block))
        return "\n\n".join(blocks)
