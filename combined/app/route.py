from __future__ import annotations

import re
from dataclasses import dataclass

from .lane import CLAUSE_SPLIT, singular, tokens, within_one_edit
from .protocol import MEMORY_TOOL_NAMES, ToolDefinition

ACTION_WORDS = {
    "create": frozenset("create build make generate draw produce compose design".split()),
    "edit": frozenset("edit adjust modify revise update change fix".split()),
    "delete": frozenset("delete remove forget erase drop".split()),
    "run": frozenset("run start launch execute begin trigger".split()),
    "compute": frozenset("compute calculate sum average total percent percentage plus minus divide multiply".split()),
    "search": frozenset("search find look browse".split()),
    "read": frozenset("read open follow summarize summarise fetch retrieve get recall".split()),
    "discover": frozenset("check inspect discover".split()),
    "list": frozenset("list show display".split()),
    "save": frozenset("remember note save store".split()),
    "send": frozenset("send email forward mail message".split()),
    "configure": frozenset("set switch change use enable disable turn".split()),
    "status": frozenset("status progress state".split()),
}
RESOURCE_WORDS = {
    "image": frozenset("image picture photo render illustration drawing".split()),
    "link": frozenset("link page url source result".split()),
    "web": frozenset("web online internet news".split()),
    "memory": frozenset("memory memories note".split()),
    "subject": frozenset("subject topic".split()),
    "artifact": frozenset("artifact app site dashboard".split()),
    "job": frozenset("job task queue script".split()),
    "code": frozenset("code javascript sandbox".split()),
    "tool": frozenset("tool".split()),
    "feedback": frozenset("feedback bug".split()),
    "theme": frozenset("theme mode".split()),
    "model": frozenset("model".split()),
    "effort": frozenset("reasoning effort thinking".split()),
    "preferences": frozenset("preference".split()),
    "capability": frozenset("capability feature ability option setting".split()),
    "calendar": frozenset("calendar".split()),
    "email": frozenset("email mail inbox".split()),
    "accent": frozenset("accent".split()),
    "font": frozenset("font typeface".split()),
    "workflow": frozenset("workflow routine automation".split()),
    "schedule": frozenset("schedule scheduled recurring".split()),
}
SETTING_RESOURCES = ("effort", "accent", "font", "model", "theme")
NAME_NOISE = frozenset("for chat main agent events event in".split())
IMPLIED_RESOURCE = {"draw": "image", "sketch": "image", "paint": "image"}
QUESTION_ANYWHERE = re.compile(r"\?|\bwhat'?s\b|\bwhat is\b|\bwhat\b", re.I)
NEGATION_LEAD = re.compile(r"^\s*(?:(?:hey|hi|hello|ok|okay|so|well)[,:\-—\s]*)*(?:please\s+)?(?:don'?t|do not|dont|no need to|no need for|never|skip|without|leave [a-z ]+ alone|no [a-z\- ]+ please)\b", re.I)
LEAD_INS = re.compile(r"^\s*(?:(?:hey|hi|hello|ok|okay|so|well|right|sure)[,:\-—\s]+)+", re.I)
QUESTION_WORD = re.compile(r"^\s*(?:what|which|who|where|when|how|did|do|does|is|are|can|could)\b", re.I)
COURTESY = frozenset("please thanks thank you it one ok okay so the a an my and to on of at up now again this that these those them then just also".split())
DESCRIPTORS = frozenset("new saved existing quick small little".split())
DEICTIC = frozenset("it that this them those these one".split())
QUOTED = re.compile(r"[\"“”]([^\"“”]{2,80})[\"“”]")
FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?")
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


@dataclass(frozen=True)
class Step:
    action: str
    resource: str


@dataclass(frozen=True)
class Route:
    tools: tuple[str, ...] = ()
    basis: str = ""

    def __bool__(self) -> bool:
        return bool(self.tools)


@dataclass(frozen=True)
class Capability:
    name: str
    actions: frozenset[str]
    resources: frozenset[str]
    named_resources: frozenset[str]
    described_verbs: frozenset[str]


CUE_PATTERNS = (NEGATION_LEAD, LEAD_INS)
PATTERN_WORDS = frozenset(word for pattern in CUE_PATTERNS for word in re.findall(r"[a-z']{4,}", pattern.pattern))
VOCABULARY = frozenset().union(*ACTION_WORDS.values(), *RESOURCE_WORDS.values(), COURTESY, PATTERN_WORDS)
BY_LENGTH: dict[int, tuple[str, ...]] = {}
for _word in sorted(VOCABULARY):
    BY_LENGTH.setdefault(len(_word), ())
    BY_LENGTH[len(_word)] = BY_LENGTH[len(_word)] + (_word,)


def inflection_of(word: str, candidate: str) -> bool:
    return word.startswith(candidate) and word[len(candidate):] in ("s", "d", "ed", "ing")


def transposed(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def only(candidates: list[str]) -> str | None:
    return candidates[0] if len(candidates) == 1 else None


def snap_word(word: str) -> str:
    lower = word.lower()
    if len(lower) < 4 or lower in VOCABULARY or not lower.isalpha():
        return word
    if len(lower) == 4:
        return only([candidate for candidate in BY_LENGTH.get(4, ()) if transposed(lower, candidate)]) or word
    for length in (len(lower), len(lower) - 1, len(lower) + 1):
        near = [candidate for candidate in BY_LENGTH.get(length, ()) if within_one_edit(lower, candidate) and not inflection_of(lower, candidate)]
        if near:
            return only(near) or word
    return word


def snap_spelling(text: str) -> str:
    return WORD.sub(lambda match: snap_word(match.group(0)), text)


def forms(word: str) -> tuple[str, ...]:
    shapes = [word, singular(word)]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        shapes.append(word[:-1])
    return tuple(shapes)


def concepts(words: list[str], table: dict[str, frozenset[str]]) -> set[str]:
    found: set[str] = set()
    for word in words:
        for concept, vocabulary in table.items():
            if any(shape in vocabulary for shape in forms(word)):
                found.add(concept)
    return found


def question_shaped(text: str) -> bool:
    return bool(QUESTION_WORD.match(LEAD_INS.sub("", text, count=1)))


def capability_of(tool: ToolDefinition) -> Capability:
    name_words = [w for w in tool.name.lower().split("_") if w not in NAME_NOISE]
    first_sentence = tool.description.split(".")[0]
    described = tokens(first_sentence)
    named_actions = concepts(name_words, ACTION_WORDS)
    described_actions = concepts(described, ACTION_WORDS)
    actions = (named_actions | ({"compute"} & described_actions)) if named_actions else described_actions
    named = concepts(name_words, RESOURCE_WORDS)
    resources = named or concepts(described, RESOURCE_WORDS)
    if tool.name in MEMORY_TOOL_NAMES:
        resources = resources | {"memory"}
    verbs = {w for w in described if any(w in vocabulary for vocabulary in ACTION_WORDS.values())}
    return Capability(tool.name, frozenset(actions), frozenset(resources), frozenset(named), frozenset(verbs))


class Catalog:
    def __init__(self, tools: list[ToolDefinition]) -> None:
        self.capabilities = [capability_of(tool) for tool in tools]
        self.names = {cap.name for cap in self.capabilities}

    def find(self, action: str, resource: str) -> str | None:
        wanted = {resource}
        with_resource = [cap for cap in self.capabilities if wanted <= cap.resources]
        if not with_resource:
            return None
        acting = [cap for cap in with_resource if action in cap.actions]
        if not acting:
            return None
        acting.sort(key=lambda cap: (len(cap.named_resources ^ wanted), len(cap.resources), cap.name))
        return acting[0].name

    def resource_of_verb(self, verb: str) -> str | None:
        owners = [cap for cap in self.capabilities if verb in cap.described_verbs and cap.named_resources]
        if len(owners) != 1:
            return None
        return sorted(owners[0].named_resources)[0]


def clauses_of(request: str) -> list[str]:
    return [clause.strip() for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]


def affirmative_text(request: str) -> str:
    return " ".join(clause for clause in clauses_of(request) if not NEGATION_LEAD.match(clause))


def content_words(request: str, resource_words: set[str]) -> list[str]:
    kept: list[str] = []
    for word in tokens(request):
        base = singular(word)
        if word in COURTESY or base in COURTESY or word in DESCRIPTORS or base in DESCRIPTORS:
            continue
        if word in resource_words or base in resource_words:
            continue
        if any(word in vocabulary or base in vocabulary for vocabulary in ACTION_WORDS.values()):
            continue
        kept.append(word)
    return kept


def underspecified(request: str, steps: list[Step]) -> bool:
    if not steps:
        return False
    resource_words = set().union(*RESOURCE_WORDS.values()) | {"color", "update", "reasoning", "effort"}
    words = tokens(request)
    remaining = content_words(request, resource_words)
    if any(w in DEICTIC for w in words) and not QUOTED.search(request) and not FIGURE.search(request):
        return len([w for w in remaining if w not in DEICTIC]) <= 1
    return len(remaining) == 0


def web_steps(text: str, actions: set[str], resources: set[str]) -> list[Step]:
    searching = bool(actions & {"search", "read"})
    asks = bool(QUESTION_ANYWHERE.search(text))
    if not ("web" in resources and (asks or actions)) and not (searching and "link" in resources):
        return []
    return [Step("search", "web")]


def workflow_steps(text: str, actions: set[str], resources: set[str]) -> list[Step]:
    scheduled_runs = "schedule" in resources and ("workflow" in resources or "run" in actions)
    if "workflow" not in resources and not scheduled_runs:
        return []
    asks_listing = bool(actions & {"list"} or re.search(r"\b(?:what|which|how many)\b", text, re.I))
    if asks_listing and not actions & {"create"}:
        return [Step("list", "schedule" if scheduled_runs else "workflow")]
    if "workflow" in resources and ("create" in actions or re.search(r"\bset up\b", text, re.I)):
        return [Step("create", "workflow")]
    return []


def image_steps(text: str, actions: set[str], resources: set[str], catalog: Catalog) -> list[Step]:
    implied = any(catalog.resource_of_verb(word) == "image" or IMPLIED_RESOURCE.get(word) == "image" for word in tokens(text)) and not resources - {"image"}
    if "image" not in resources and not implied:
        return []
    steps: list[Step] = []
    if "create" in actions or implied:
        steps.append(Step("create", "image"))
    if re.search(r"\b(?:brighten|adjust|crop|sharpen|darken)\b", text, re.I) or ("edit" in actions and not steps):
        steps.append(Step("edit", "image"))
    return steps


def setting_steps(text: str, actions: set[str], resources: set[str]) -> list[Step]:
    if "preferences" in resources and "tool" in resources:
        return [Step("configure", "preferences")]
    wanted = [r for r in SETTING_RESOURCES if r in resources]
    if not wanted or not actions & {"configure", "create", "edit"}:
        return []
    return [Step("configure", wanted[0])]


def catalog_steps(request: str, catalog: Catalog) -> list[Step]:
    text = snap_spelling(affirmative_text(request))
    banned = prohibited_resources(snap_spelling(request))
    words = tokens(text)
    actions = concepts(words, ACTION_WORDS)
    resources = concepts(words, RESOURCE_WORDS) - banned
    computing = "compute" in actions and bool(FIGURE.search(text)) and "code" not in banned
    if "capability" in resources and question_shaped(text) and not (set(SETTING_RESOURCES) & resources and re.search(r"^\s*(?:use|set|switch|make|change)\b", text, re.I)):
        return [Step("discover", "capability")]
    if "feedback" in resources:
        return [Step("send", "feedback")]
    settings = setting_steps(text, actions, resources)
    if settings:
        return settings
    if computing:
        return [Step("compute", "code")]
    if "job" in resources and "run" in actions and "workflow" not in resources:
        return [Step("run", "job")]
    if "calendar" in resources:
        if actions & {"search", "list"}:
            return [Step("search", "calendar")]
        return [Step("create", "calendar")]
    remembering = re.search(r"\bremember that\b", text, re.I)
    if "memory" in resources and ("delete" in actions or "bin" in words):
        return [Step("delete", "memory")]
    if "memory" in resources and "edit" in actions:
        return [Step("edit", "memory")]
    if remembering and "effort" not in resources:
        return [Step("save", "memory")]
    workflow = workflow_steps(text, actions, resources)
    if workflow:
        return workflow
    if "artifact" in resources and "create" in actions:
        return [Step("create", "artifact")]
    image = image_steps(text, actions, resources, catalog)
    if image:
        return image
    return web_steps(text, actions, resources)


def resolve(steps: list[Step], catalog: Catalog) -> tuple[str, ...]:
    names: list[str] = []
    for step in steps:
        name = catalog.find(step.action, step.resource)
        if name and name not in names:
            names.append(name)
    return tuple(names)


def negated_clauses(request: str) -> list[str]:
    return [clause for clause in clauses_of(request) if NEGATION_LEAD.match(clause)]


def prohibited_resources(request: str) -> set[str]:
    banned: set[str] = set()
    for clause in negated_clauses(request):
        words = tokens(clause)
        banned |= concepts(words, RESOURCE_WORDS)
        if "search" in concepts(words, ACTION_WORDS) and "memory" not in concepts(words, RESOURCE_WORDS):
            banned.add("web")
    return banned


def order_by_route(tools: list[ToolDefinition], route: Route) -> list[ToolDefinition]:
    rank = {name: position for position, name in enumerate(route.tools)}
    return sorted(tools, key=lambda tool: rank.get(tool.name, len(rank)))


def route_by_catalog(request: str, tools: list[ToolDefinition]) -> Route:
    catalog = Catalog(tools)
    steps = catalog_steps(request, catalog)
    if underspecified(snap_spelling(request), steps):
        return Route((), "catalog: the request names no object to act on")
    return Route(resolve(steps, catalog), "catalog")
