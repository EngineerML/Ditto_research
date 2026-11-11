"""Calendar dates for notes that date an event by its distance from another one.

A note can say "reference call, 13 days after the board review" while another note dates the board review. For a
question about what came immediately before or after an event, this works out the calendar date of each such note
from the note that dates its anchor, so the events can be put in order. No model call; the lines are advisory.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}
MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{MONTH}\s*,?\s+(\d{{4}})\b", re.IGNORECASE)
MONTH_DAY_YEAR = re.compile(rf"\b{MONTH}\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s+(\d{{4}})\b", re.IGNORECASE)
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
NUMBER_WORDS = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
DISTANCE = re.compile(
    r"\b(\d{1,3}|a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\s+"
    r"(day|week)s?\s+(after|before|following|ahead of|prior to)\s+(?:the\s+|that\s+|our\s+)?"
    r"([a-z][a-z'\- ]{1,48}?)(?=\s*(?:[.,;:!?)\]}\"”]|$|\s+(?:and|but|which|so|when|for|on|in|at|with)\b))",
    re.IGNORECASE)
BEFORE = ("before", "ahead of", "prior to")
ASKS_ADJACENT = re.compile(
    r"\b(?:immediately|right|directly|just|straight)\s+(?:after|before|following|preceding)\b"
    r"|\bcame (?:after|before|next)\b|\b(?:followed|preceded)\b|\bnext (?:after|one after)\b", re.IGNORECASE)
SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)")
FILING_STAMP = re.compile(r"^\W*(?:\d{4}-\d{2}-\d{2}\s*:\s*)?")
HEADER = ("Dates worked out by code for notes that date something by its distance from another event, from the note "
          "that dates that event; not checked, the notes decide:")
MAX_LINES = 8


def valid(year: int, month: int | None, day: int) -> list[date]:
    try:
        return [date(year, month, day)] if month else []
    except ValueError:
        return []


def calendar(text: str) -> list[date]:
    found: list[date] = []
    for match in DAY_MONTH_YEAR.finditer(text):
        found += valid(int(match.group(3)), MONTHS.get(match.group(2).lower()[:3]), int(match.group(1)))
    for match in MONTH_DAY_YEAR.finditer(text):
        found += valid(int(match.group(3)), MONTHS.get(match.group(1).lower()[:3]), int(match.group(2)))
    for match in ISO_DATE.finditer(text):
        found += valid(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return found


def written(day: date) -> str:
    return f"{day.day} {day.strftime('%B')} {day.year}"


def days_of(word: str, unit: str) -> int:
    count = int(word) if word.isdigit() else NUMBER_WORDS[word.lower()]
    return count * (7 if unit.lower() == "week" else 1)


def sentences(texts: list[str]) -> list[str]:
    parts = (FILING_STAMP.sub("", part.strip()) for text in texts for part in SENTENCE.findall(text))
    return list(dict.fromkeys(part for part in parts if part))


def anchor_date(anchor: str, own: str, pool: list[str]) -> date | None:
    days = {day for sentence in pool if sentence != own and anchor in sentence.lower() and not DISTANCE.search(sentence)
            for day in calendar(sentence)}
    return days.pop() if len(days) == 1 else None


def distance_view(message: str, texts: list[str]) -> str:
    if not ASKS_ADJACENT.search(message):
        return ""
    pool = sentences(texts)
    lines: dict[tuple[str, str], str] = {}
    for sentence in pool:
        for match in DISTANCE.finditer(sentence):
            anchor = match.group(4).strip().lower()
            base = anchor_date(anchor, sentence, pool)
            key = (sentence[max(0, match.start() - 40):match.start()].lower().split(":")[-1].strip(), match.group(0).lower())
            if base is None or key in lines:
                continue
            step = days_of(match.group(1), match.group(2))
            day = base - timedelta(days=step) if match.group(3).lower() in BEFORE else base + timedelta(days=step)
            lines[key] = f"- “{sentence}”: the {anchor} is dated {written(base)}, so this falls on {written(day)}."
    return HEADER + "\n" + "\n".join(list(lines.values())[:MAX_LINES]) + "\n\n" if lines else ""

