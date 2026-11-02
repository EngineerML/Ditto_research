from __future__ import annotations

import re

from .protocol import RunRequest, ToolDefinition

# A tool whose own description says it works only once its connector or integration is linked or connected is not
# available until that link exists (availability, W4). The description is the request's own word on that (W10), and
# the public tool contract agrees: dittobench-api PROTOCOL.md and the starter-kit README say the workspace has linked
# none of these connectors and that every call to one is refused "not connected" and performs nothing.
#
# Such a tool is left out before routing and before every menu the model sees, unless the request itself says its app
# is linked or connected; then it stays. Every other tool stays exactly as the request supplied it (name, description,
# schema and order). The tests stay inside one sentence; a dot inside a name such as monday.com does not end it.
WITHIN_SENTENCE = r"(?:[^.]|\.(?=\S))"
UNLINKED = re.compile(
    rf"\b(?:needs?|requires?)\s+(?:(?:the|a|an|your)\s+)?(?P<app>{WITHIN_SENTENCE}{{1,60}}?)\s+(?:connectors?|integrations?|connections?)\b{WITHIN_SENTENCE}{{0,40}}?\b(?:linked|connected|set up|authori[sz]ed)\b",
    re.IGNORECASE,
)
SENTENCE = re.compile(rf"{WITHIN_SENTENCE}+")
LINK_WORDS = re.compile(r"\b(?:linked|connected|hooked up|set up|authori[sz]ed|integrated)\b", re.IGNORECASE)
NOT_LINKED = re.compile(r"\b(?:not|never|no longer|without|unlinked|disconnected|isn't|aren't|wasn't|hasn't|haven't)\b|n't\b", re.IGNORECASE)


def needed_link(tool: ToolDefinition) -> str | None:
    """The app a tool's description says must be linked first, or "" when it names none; None for any other tool."""
    found = UNLINKED.search(tool.description or "")
    if found is None:
        return None
    return found.group("app").strip()


def says_linked(app: str, text: str) -> bool:
    """Whether one sentence of the request names the app as linked or connected, without negating it."""
    if not app:
        return False
    named = re.compile(rf"(?<![\w.]){re.escape(app)}(?![\w])", re.IGNORECASE)
    return any(named.search(part) and LINK_WORDS.search(part) and not NOT_LINKED.search(part) for part in SENTENCE.findall(text))


def usable(req: RunRequest) -> tuple[list[ToolDefinition], int, int]:
    """The tools the request can use, how many were left out as unlinked, and how many stayed because it says linked."""
    text = f"{req.system_prompt}\n{req.user_input}"
    kept: list[ToolDefinition] = []
    left_out = stayed = 0
    for tool in req.tools:
        app = needed_link(tool)
        if app is None:
            kept.append(tool)
        elif says_linked(app, text):
            kept.append(tool)
            stayed += 1
        else:
            left_out += 1
    return kept, left_out, stayed
