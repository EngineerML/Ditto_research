"""One request's tool offer: the tools listed to the model and every tool the request supplied.

The connector step (`connectors.linked_tools`) decides which tools are listed; it removes nothing. A tool it leaves
unlisted stays callable through every lane: the action surface and the records lane know it and read its schema, and
the executor sends it. Once the case reaches an unlisted tool (the model calls it, or a tool result such as a tool
search names it), it is listed from the next turn on. Memory tools are always listed.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any

from .protocol import MEMORY_TOOL_NAMES


class Offer:
    def __init__(self, supplied: list[Any], listed: list[str]) -> None:
        self.definitions = {tool.name: tool for tool in supplied}
        self.shown = (set(listed) | MEMORY_TOOL_NAMES) & set(self.definitions)
        self._reached: list[str] = []
        names = sorted(self.definitions, key=len, reverse=True)
        self._named = (
            re.compile(r'\b(?:' + '|'.join(map(re.escape, names)) + r')\b')
            if names
            else None
        )

    def supplies(self, name: str) -> bool:
        return name in self.definitions

    def definition(self, name: str) -> Any:
        return self.definitions.get(name)

    def reach(self, called: str, output: str = '') -> None:
        found = ([called] if called in self.definitions else []) + (
            self._named.findall(output)
            if self._named is not None and output
            else []
        )
        for name in found:
            if name not in self.shown and name not in self._reached:
                self._reached.append(name)

    def reached(self) -> list[Any]:
        return [self.definitions[name] for name in self._reached]


OFFER: ContextVar[Offer | None] = ContextVar('offer', default=None)


def listed_extra(present: set[str]) -> list[Any]:
    """Tools the request supplied that the case has reached or that are always listed, and are not in `present`."""
    offer = OFFER.get()
    if offer is None:
        return []
    always = [
        offer.definitions[name]
        for name in sorted(offer.shown)
        if name not in present and name in MEMORY_TOOL_NAMES
    ]
    return always + [
        tool for tool in offer.reached() if tool.name not in present
    ]
