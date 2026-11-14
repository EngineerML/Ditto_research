"""Hold back a create call when the request asks for a new item only if none exists and one is already listed.

A message like "check whether we already track it in QuickBooks, and if we don't, file it" makes the new item
conditional. When an identifier the earlier results gave (an incident id such as MOV-3498) already appears in an item a
listing of that same app returned, the first create call to that app is not sent; the model is told which listed item
names it, and it decides: report that item, or send the call again if a new one is still needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol

CONDITIONAL_NEW = re.compile(
    r"\b(?:only if|unless|if (?:we|you|they|there|it|one)(?:'re| are| is|'s)? ?(?:don't|do not|doesn't|does not|isn't|is not|"
    r"aren't|are not|haven't|have not|hasn't|has not|not)|if (?:it'?s|it is) not|if (?:no|none)\b|not already)",
    re.IGNORECASE)
CREATE_VERB = re.compile(r"_(?:create|add|new|file|open|log|record)(?:_|$)")
LIST_VERB = re.compile(r"_(?:list|search|find|get|query|lookup)(?:_|$)")
IDENTIFIER = re.compile(r"\b[A-Z][A-Z0-9]{1,7}-\d{2,7}\b")
ITEM_SPLIT = re.compile(r"(?<=[;.])\s+|\n")
REGION = re.compile(r"\b(?:us|eu|ap|sa|ca|me|af)-(?:north|south)?(?:east|west|central|north|south)(?:-\d)?\b", re.IGNORECASE)
PAST = re.compile(r"\b(?:resolved|closed|last (?:week|month)|previous|earlier)\b")
NO_ITEM = re.compile(r"\bno (?:item|ticket|issue|deal|match|record|entry)", re.IGNORECASE)
TRACKED_NOTE = ("Not sent, so nothing was created: {name} would add a new item, but the earlier {lister} result already "
                "lists one for {identifier}: \"{item}\". The message asks for a new item only if none exists, so it is "
                "already tracked as {ref}: tell the user that reference and that nothing new was filed. Only if a new "
                "item is still needed, send the call again and it goes out.")


TRACKED_REPLY_NOTE = ("A note on the reply above: the {name} call was not sent, so nothing new was created, and the "
                      "earlier listing already holds {identifier} as {ref}. Write the reply again from the results: "
                      "give what the user asked for, say that {identifier} is already tracked as {ref}, and that "
                      "nothing new was filed.")


@dataclass(frozen=True)
class TrackedHold:
    note: str
    name: str
    identifier: str
    ref: str


class Receipt(Protocol):
    name: str
    output: str
    state: str


def app_of(name: str) -> str:
    return name.split("_", 1)[0]


def listed_item(identifier: str, output: str) -> str:
    for part in ITEM_SPLIT.split(output):
        if identifier in part:
            return part.strip().strip('"')[:200]
    return identifier


def current_identifiers(output: str, regions: set[str]) -> set[str]:
    """Identifiers another source gives for something current: not marked resolved, and on the user's region when
    the message names one."""
    found = set()
    for match in IDENTIFIER.finditer(output):
        before = output[max(0, match.start() - 40):match.start()].lower()
        nxt = IDENTIFIER.search(output, match.end())
        span = output[match.start():nxt.start() if nxt else len(output)].lower().split(". ", 1)[0]
        if PAST.search(before.rsplit(".", 1)[-1]) or PAST.search(span):
            continue
        if regions and not any(region in span for region in regions):
            continue
        found.add(match.group(0))
    return found


def already_tracked(name: str, message: str, ledger: Iterable[Receipt], completed: str) -> TrackedHold | None:
    if "_" not in name or not CREATE_VERB.search(name) or not CONDITIONAL_NEW.search(message):
        return None
    receipts = [receipt for receipt in ledger if receipt.state == completed]
    app = app_of(name)
    regions = {region.lower() for region in REGION.findall(message)}
    elsewhere = {token for receipt in receipts if app_of(receipt.name) != app for token in current_identifiers(receipt.output, regions)}
    for receipt in receipts:
        if app_of(receipt.name) != app or not LIST_VERB.search(receipt.name):
            continue
        for identifier in IDENTIFIER.findall(receipt.output):
            item = listed_item(identifier, receipt.output)
            if identifier in elsewhere and not NO_ITEM.search(item):
                ref = next((token for token in IDENTIFIER.findall(item) if token != identifier), f"\"{item}\"")
                note = TRACKED_NOTE.format(name=name, lister=receipt.name, identifier=identifier, item=item, ref=ref)
                return TrackedHold(note, name, identifier, ref)
    return None


UNLISTED_NOTE = ("Not sent, so nothing was created: the message asks for a new item only if none exists, and no {app} "
                 "listing has been read in this request yet. Call one of {app}'s listing or search tools first and look "
                 "for an item on this; only if none is there, send {name} again and it goes out.")


def unlisted_create(name: str, message: str, ledger: Iterable[Receipt], completed: str) -> str | None:
    """A create call to an app the message says to check first, sent before any listing from that app was read."""
    if "_" not in name or not CREATE_VERB.search(name) or not CONDITIONAL_NEW.search(message):
        return None
    app = app_of(name)
    if app.lower() not in message.lower().replace(" ", ""):
        return None
    if any(app_of(receipt.name) == app and LIST_VERB.search(receipt.name) and receipt.state == completed for receipt in ledger):
        return None
    return UNLISTED_NOTE.format(app=app, name=name)
