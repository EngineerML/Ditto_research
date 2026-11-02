from __future__ import annotations

import re

from .protocol import ToolDefinition

# A tool whose own description says it works only once its connector or integration is linked or connected cannot
# run in a workspace where nothing links it. Such tools are left out before routing and before every menu the model
# sees; every other tool stays exactly as the request supplied it (name, description, schema and order). The test
# stays inside one sentence; a dot inside a name such as monday.com does not end it.
WITHIN_SENTENCE = r"(?:[^.]|\.(?=\S))"
UNLINKED = re.compile(
    rf"\b(?:needs?|requires?)\b{WITHIN_SENTENCE}{{0,80}}?\b(?:connectors?|integrations?|connections?)\b{WITHIN_SENTENCE}{{0,40}}?\b(?:linked|connected|set up|authori[sz]ed)\b",
    re.IGNORECASE,
)


def unlinked(tool: ToolDefinition) -> bool:
    return bool(UNLINKED.search(tool.description or ""))


def usable(tools: list[ToolDefinition]) -> tuple[list[ToolDefinition], int]:
    kept = [tool for tool in tools if not unlinked(tool)]
    return kept, len(tools) - len(kept)
