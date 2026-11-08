from __future__ import annotations

from typing import Any

from .lane import CLAUSE_SPLIT, GENERIC_NAME_WORDS, LOOSE_SYNONYMS, READ_SYNONYMS, VERB_INITIAL, reads_state, singular, tokens
from .offer import OFFER, listed_extra
from .protocol import ToolDefinition
from .route import Route, order_by_route
from .tools import openai_tools


def name_forms(word: str) -> set[str]:
    forms = {word, singular(word)}
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])
    return forms


def tool_terms(tool: ToolDefinition) -> set[str]:
    terms = {form for word in tool.name.split("_") if word not in GENERIC_NAME_WORDS and len(word) > 2 for form in name_forms(word)}
    if reads_state(tool.name):
        terms |= {word for word, capability in READ_SYNONYMS.items() if capability in terms}
    return terms


def addressed_verbs(request: str) -> set[str]:
    leads = set()
    for clause in CLAUSE_SPLIT.split(request):
        if not clause or not clause.strip():
            continue
        lead = VERB_INITIAL.match(clause)
        if lead:
            leads.add(lead.group(1).lower())
    return {singular(lead) for lead in leads if lead in LOOSE_SYNONYMS}


def presentation_order(tools: list[ToolDefinition], request: str) -> list[ToolDefinition]:
    words = {singular(word) for word in tokens(request)} - addressed_verbs(request)

    def key(item: tuple[int, ToolDefinition]) -> tuple[int, int, int, int]:
        position, tool = item
        matches = len(words & tool_terms(tool))
        if matches:
            return (0, -matches, 0 if reads_state(tool.name) else 1, position)
        return (1, 0, 0, position)

    return [tool for _, tool in sorted(enumerate(tools), key=key)]


class Surface:
    def __init__(self, tools: list[ToolDefinition], request: str, route: Route = Route()) -> None:
        self.catalog = list(tools)
        self.by_name = {tool.name: tool for tool in self.catalog}
        self.ordered = order_by_route(presentation_order(self.catalog, request), route)

    def knows(self, name: str) -> bool:
        # Every tool the request supplied is callable, listed or not.
        offer = OFFER.get()
        return name in self.by_name or (offer is not None and offer.supplies(name))

    def schema(self, name: str) -> dict[str, Any]:
        offer = OFFER.get()
        tool = self.by_name.get(name) or (offer.definition(name) if offer is not None else None)
        return tool.parameters if tool is not None and isinstance(tool.parameters, dict) else {}

    def required(self, name: str) -> list[str]:
        return list(self.schema(name).get("required") or [])

    def visible(self) -> list[dict[str, Any]]:
        # The listed tools, then any unlisted tool the case has reached (called, or named by a tool result).
        return openai_tools(self.ordered + listed_extra(set(self.by_name)))
