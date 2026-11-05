"""Choose which listed tools a request's model calls are offered.

Bench 16 lists about 235 tools per request. Most of them belong to apps (connectors and add-ons) the request never
mentions, and every turn that carries them pays about 7,100 prompt tokens for them. This keeps every tool a request
can plausibly need and leaves out app tools nothing in the request points to.

The decision reads only the request's own text and each tool's own name and description. It uses no tool-name list,
app list, seed or bench version.

- A tool is *app-scoped* when its description names a brand (a capitalised name inside the sentence, or a domain such
  as monday.com) that its own name starts with: `slack_post_message` ("... the user's Slack workspace"),
  `mongodb_find_documents` ("... a MongoDB Atlas collection"), `gcp_list_instances` ("Show Google Cloud VMs.").
- Mail and the calendar are the assistant's own channels: a request reaches them without naming the app ("send them
  the numbers", "put it on my schedule"). A tool whose first sentence is about mail or the calendar, or whose name
  starts with a mail or calendar word, is general.
- General tools (memory, web, images, code, workflows, settings, capability lookup, tool search, mail, calendar) are
  always offered.
- An app-scoped tool is offered when the request names its app: a word of the brand or the word its name starts with,
  whole, or one edit off for words of five letters or more.
- Names in `keep` stay offered: what a case has already shown it needs (an earlier turn's list, a call the model
  made, a tool a result or the model named).

`select` returns the offered names in catalog order; each tool keeps its place, name, description and schema.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9]*(?:[.'][A-Za-z0-9]+)*")
CAPITALISED = re.compile(r"(?<![.!?]\s)(?<!^)\b((?:[A-Z]|[0-9]+[A-Z])[A-Za-z0-9]*(?:\.[a-z]+)?(?:\s+[A-Z][A-Za-z0-9]*)*)")
DOMAIN_NAME = re.compile(r"\b([a-z][a-z0-9]+\.(?:com|io|ai|app|net|org))\b")
OWN_PRODUCT = {"ditto"}
PERSONAL_CHANNEL = re.compile(r"\b(?:e-?mail|mail|calendar)\b", re.IGNORECASE)
PERSONAL_NAME = re.compile(r"(?:mail|calendar)$")
FIRST_SENTENCE = re.compile(r"^.*?(?:[.!?](?:\s|$)|$)", re.DOTALL)


@dataclass(frozen=True)
class ToolView:
    name: str
    brand_words: tuple[str, ...] = ()

    @property
    def app_scoped(self) -> bool:
        return bool(self.brand_words)


def brand_of(name: str, description: str) -> tuple[str, ...]:
    """The words of the brand the description names and the tool's name starts with, lowercased; () if none."""
    parts = name.lower().split("_")
    phrases = [m.group(1) for m in CAPITALISED.finditer(description or "")] + DOMAIN_NAME.findall(description or "")
    for phrase in phrases:
        words = [w.lower() for w in re.split(r"\s+", phrase)]
        if words[0] in OWN_PRODUCT:
            continue
        bare = [re.sub(r"\.[a-z]+$", "", w) for w in words]
        for k in range(1, len(parts)):
            prefix = "".join(parts[:k])
            # the brand, a leading part of it ("MongoDB" of "MongoDB Atlas"), its last word ("Calendar" of
            # "Google Calendar") or the initials of a leading part ("gcp" for "Google Cloud VMs") is the name's prefix
            leading = any("".join(bare[:j]) == prefix for j in range(1, len(bare) + 1))
            short = any(len(prefix) <= j + 1 and prefix.startswith("".join(w[0] for w in bare[:j])) for j in range(2, len(bare) + 1))
            if leading or bare[-1] == prefix or short:
                return tuple(dict.fromkeys(bare + parts[:k]))
    return ()


def view(tool: dict) -> ToolView:
    name = tool.get("name") or ""
    description = tool.get("description") or ""
    if PERSONAL_NAME.search(name.split("_")[0]) or PERSONAL_CHANNEL.search(FIRST_SENTENCE.match(description).group(0)):
        return ToolView(name)
    return ToolView(name, brand_of(name, description))


def one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def request_words(text: str) -> set[str]:
    raw = {re.sub(r"'s?$", "", w.lower()) for w in WORD.findall(text)}
    return raw | {w.replace(".", "") for w in raw} | {re.sub(r"\.[a-z]+$", "", w) for w in raw}


def mentioned(brand: tuple[str, ...], words: set[str]) -> bool:
    for word in brand:
        if len(word) < 3:
            continue
        if word in words:
            return True
        if len(word) >= 5 and any(len(w) >= 5 and one_edit(word, w) for w in words):
            return True
    return False


def select(tools: list[dict], user_text: str, system_text: str = "", keep: set[str] | None = None) -> tuple[list[str], dict[str, str]]:
    """Names to offer, in catalog order, and why each one is offered (general, kept or named)."""
    keep = keep or set()
    words = request_words(f"{system_text}\n{user_text}")
    out, why = [], {}
    for v in map(view, tools):
        reason = ""
        if not v.app_scoped:
            reason = "general"
        elif v.name in keep:
            reason = "kept"
        elif mentioned(v.brand_words, words):
            reason = "named"
        if reason:
            out.append(v.name)
            why[v.name] = reason
    return out, why
