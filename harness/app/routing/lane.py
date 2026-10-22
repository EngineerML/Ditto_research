from __future__ import annotations

import re
from dataclasses import dataclass

from app.memory.retrieval import SENTENCE_START, STOPWORDS, UserIndex
from app.protocol import MEMORY_TOOL_NAMES, ToolDefinition

ACTION = "action"
RECORDS = "records"

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
GENERIC_NAME_WORDS = frozenset("search create set list run execute get file read main chat for team status in save update delete send discover".split())
READ_PREFIXES = ("list_", "search_", "discover_", "read_", "get_", "fetch_", "find_", "lookup_")
READ_SYNONYMS = {"task": "job", "tasks": "job", "queue": "job", "queued": "job", "automatic": "schedule", "scheduled": "schedule", "app": "capabilities", "feature": "capabilities", "features": "capabilities", "option": "capabilities", "options": "capabilities", "setting": "capabilities", "settings": "capabilities", "control": "capabilities", "switch": "capabilities", "help": "capabilities", "calendar": "calendar", "web": "web", "online": "web", "internet": "web"}
DO_VERBS = frozenset("make set change switch use create build run start kick dispatch send email mail schedule put add delete remove forget bin update save search find look pull open read draw generate edit tweak file report check plan split turn spin fetch research see forward pass shoot grab crunch compute normalize calculate take list summarize summarise brighten adjust enable disable move retry try apply execute reason skip describe paint outline talk google browse book crop warm resize convert post launch trigger sort begin proceed handle deploy refactor scrape rework touch bump explain break correct fix".split())
FRAMING_VERBS = frozenset("use read look see find search pull open fetch grab take apply list skip google browse research summarize summarise describe explain reason talk compute normalize calculate crunch handle try".split())
NON_VERBS = frozenset("my our i i'm i've we the a an this that these those it its one for on in at when if what which who where how why did do does is are was were will would could can should has have had thanks hey hi ok okay so yes no ditto".split())
LIVE_CUES = re.compile(r"\b(latest|current(?:ly)?|right now|at (?:\w+ )?now|up[- ]to[- ]date|live|online|the web|news|today'?s?|nowadays|these days|changed since|actually changed|what'?s new)\b", re.I)
ARITHMETIC = re.compile(r"\b(percent|percentage|sum|average|mean|total|times|minus|plus|split|divide|divided|compound|spread|multiply|normalize|fractions?|tip|median|crunch|calc(?:ulation)?)\b", re.I)
DIGITS = re.compile(r"\d")
QUESTION = re.compile(r"\?\s*$|^\s*(?:what|which|who|whom|whose|where|when|how|why|did|do|does|is|are|was|were|will|would|could|can|should|has|have|had)\b", re.I)
CLAUSE_SPLIT = re.compile(r"[;—–]|\s-\s|,\s*(?:and|but|then|so)\s+|\b(?:and then|then)\b|\.\s+|\?\s+")
VERB_INITIAL = re.compile(r"^\s*(?:(?:hey|hi|hello|ok|okay|so|well|thanks|also)[,:\-—\s]*)*(?:please\s+|kindly\s+|just\s+|go ahead and\s+|now\s+|actually\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?([a-z]+)\b", re.I)
SAVE_FORM = re.compile(r"^\s*(?:please\s+)?(?:remember|note|keep in mind|bear in mind|make a note|jot down)\s+(?:that|to|this|for later|:)", re.I)
SAVE_FORM_WIDE = re.compile(r"^\s*(?:please\s+)?(?:remember|note|log|record)\s*(?:that|to|this|it|them|for later|:|\.|$)|^\s*(?:please\s+)?(?:keep|bear)\s+(?:that|this|it|them)?\s*in\s+min", re.I)
NEED_FORM = re.compile(r"\b(i need|i want|i'd like|i would like)\s+(?:you to\s+|it\s+|that\s+|this\s+|the \w+\s+|a \w+\s+)?(\w+)", re.I)
SPEECH_VERBS = frozenset("answer reply respond say state name tell give word phrase".split())
QUESTION_TAIL = re.compile(r"[^.!?]*\?")
NEGATED_OPENER = re.compile(r"^\s*(?:do|does|did|is|are|was|were|will|would|could|can|should|has|have|had)(?:\s+not|n't)\b", re.I)
QUESTION_WORD = re.compile(r"\b(?:what|what'?s|which|who|who'?s|whom|whose|where|where'?s|when|why|how)\b", re.I)
REQUEST_FORM = re.compile(r"\b(?:can|could|would|will|shall)\s+(?:i|you|we)\b", re.I)
RECALL_QUESTION = re.compile(r"\s+me\s+(?:again\s+)?how\s+(?:long|many|much)\b", re.I)
COMMON_WORDS = frozenset("email emails there their theirs these those where three getting letting reference references planned plans phone phones price prices thing things month months meant means".split())
EFFECT_VERBS = frozenset(word for word in DO_VERBS if word not in FRAMING_VERBS)
READING_VERBS = FRAMING_VERBS | SPEECH_VERBS
FETCH_VERBS = frozenset("search find look fetch pull open grab read research see browse google".split())
RECORD_NOUNS = frozenset("thread account invoice balance record records".split())
TALLY_VERBS = frozenset("sum total calculate compute tally crunch".split())
DATE_SPAN = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:19|20)\d{2}\b|\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", re.I)

OWN_RECORD_CUES = frozenset({"live"})
DETAIL_NOUNS = frozenset("email emails e-mail address addresses phone phones telephone handle handles username usernames".split())
VERB_LIKE_NOUNS = frozenset("handle handles address email".split())
VERB_LEADS = frozenset("will would can could should to they we i you must".split())
WRITE_VERBS = frozenset("create delete remove clear update change set send forward save add bin forget edit make schedule book put move run start dispatch post cancel rename replace fix define build draft write".split())
SENDING_VERBS = frozenset("email mail text message".split())
CODE_IDENTIFIER = re.compile(r"\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b")
STORED_DETAIL_REASONS = frozenset({"live", "read-capability", "imperative", "imperative-setter"})
POLITE_REQUEST = re.compile(r"^\s*(?:can|could|would|will)\s+you\s+(?:please\s+)?([a-z]+)\b", re.I)
CAUSATIVE = re.compile(r"^\s*(?:please\s+)?(?:have|get)\s+((?:[a-z']+\s+){1,3}[a-z']+)", re.I)
OUTSIDE_SOURCE = re.compile(r"\b(?:web|online|internet|google|browse|news|look (?:it|this|that) up)\b", re.I)
NAMED_KINDS = frozenset("ecqni")
POSSESSED = re.compile(r"\b(?:my|our)\s+((?:[a-z]+\s+){0,2}[a-z]+)", re.I)
POSSESSION_MODIFIERS = frozenset("current latest present own usual".split())
NAME_WORD = re.compile(r"\b[A-Z][a-z]{2,}\b")
SENTENCE_BREAK = ".?!:;—–-\"“("
PART_SPLIT = re.compile(r"[,:]")

LIVE_CUE_SPELLINGS = ("latest", "current", "currently", "online", "today", "nowadays", "right")


def fold_live_cues(request: str) -> str:
    def snap(match: re.Match) -> str:
        word = match.group(0).lower()
        if len(word) < 4 or word in LIVE_CUE_SPELLINGS:
            return match.group(0)
        return next((cue for cue in LIVE_CUE_SPELLINGS if within_one_edit(word, cue)), match.group(0))
    return WORD.sub(snap, request)


ARITHMETIC_SPELLINGS = tuple(word for word in WORD.findall(ARITHMETIC.pattern) if len(word) >= 6 and ARITHMETIC.fullmatch(word))


def fold_arithmetic_cues(request: str) -> str:
    def snap(match: re.Match) -> str:
        word = match.group(0).lower()
        if len(word) < 5 or word in ARITHMETIC_SPELLINGS:
            return match.group(0)
        return next((cue for cue in ARITHMETIC_SPELLINGS if within_one_edit(word, cue)), match.group(0))
    return WORD.sub(snap, request)


LEAD_IN = re.compile(r"^\s*([^:?!.;]{1,60}):\s+")
LEAD_IN_WORDS = 4
LEAD_IN_POINTERS = frozenset("i me it this that these those".split())
STATEMENT_SUBJECT = re.compile(r"^\s*(?:(?:also|by the way|fyi|note)[,:\-—\s]*)?(?:my|our|i|i'm|i am|i've|i'd|we|we're|for (?:long|short|my|our|the|work|client|everyday|daily|any)|when i|whenever i|on (?:my|our)|in (?:my|our)|ditto should|you should)\b", re.I)


@dataclass(frozen=True)
class Lane:
    name: str
    reason: str


def after_lead_in(request: str) -> str:
    match = LEAD_IN.match(request)
    words = tokens(match.group(1)) if match else []
    if not words or len(words) > LEAD_IN_WORDS or any(word in LEAD_IN_POINTERS for word in words):
        return ""
    return request[match.end():]


def states_own_fact(request: str) -> bool:
    return bool(STATEMENT_SUBJECT.match(request) or STATEMENT_SUBJECT.match(after_lead_in(request)))


def tokens(text: str) -> list[str]:
    return [t.lower().strip("'") for t in WORD.findall(text)]


def singular(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word


def within_one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1 or len(a) < 4:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))


def reads_state(name: str) -> bool:
    return name.startswith(READ_PREFIXES) or "_search" in name


LOOSE_SYNONYMS = frozenset(READ_SYNONYMS)


def vocabulary(tools: list[ToolDefinition]) -> tuple[dict[str, str], dict[str, str]]:
    read: dict[str, str] = {}
    write: dict[str, str] = {}
    for tool in tools:
        if tool.name in MEMORY_TOOL_NAMES:
            continue
        target = read if reads_state(tool.name) else write
        for word in tool.name.split("_"):
            if word not in GENERIC_NAME_WORDS and len(word) > 2:
                target[singular(word)] = tool.name
    for word, capability in READ_SYNONYMS.items():
        read.setdefault(word, capability)
    return read, write


def nearest(word: str, vocab: dict[str, str], lexicon: bool = True) -> str | None:
    base = singular(word)
    if base in vocab:
        return base
    if base + "s" in vocab:
        return base + "s"
    if len(base) < 5:
        return None
    if lexicon and (base in COMMON_WORDS or word in COMMON_WORDS or any(within_one_edit(base, common) for common in COMMON_WORDS)):
        return None
    for entry in vocab:
        if len(entry) >= 5 and within_one_edit(base, entry):
            return entry
    return None


def recall_question(request: str) -> bool:
    lead = VERB_INITIAL.match(request)
    return bool(lead) and lead.group(1).lower() == "remind" and bool(RECALL_QUESTION.match(request, lead.end()))


def asks(request: str, clauses: list[str], wide: bool, tails: list[str]) -> bool:
    if QUESTION.search(request) and not NEGATED_OPENER.match(request):
        return True
    if wide and recall_question(request):
        return True
    if "?" not in request:
        return False
    if any(QUESTION.search(clause.strip()) for clause in clauses):
        return True
    return wide and any(QUESTION_WORD.search(tail) and not REQUEST_FORM.search(tail) for tail in tails)


VERB_SLOT_LEADS = frozenset("and then also please to now just kindly".split())


def verb_slots(words: list[str]) -> list[str]:
    return [word for index, word in enumerate(words) if index == 0 or words[index - 1] in VERB_SLOT_LEADS]


def framing_only(clause: str, words: list[str], read: dict[str, str], write: dict[str, str], lexicon: bool) -> bool:
    lead = VERB_INITIAL.match(clause)
    verb = lead.group(1).lower() if lead else ""
    if verb not in FRAMING_VERBS and verb not in SPEECH_VERBS:
        return False
    if any(word in EFFECT_VERBS for word in verb_slots(words)):
        return False
    return not any(nearest(word, read, lexicon) or nearest(word, write, lexicon) for word in words)


def record_anchor(request: str) -> bool:
    for word in tokens(request):
        base = singular(word)
        if base in RECORD_NOUNS:
            return True
        if len(base) >= 5 and any(within_one_edit(base, noun) for noun in RECORD_NOUNS):
            return True
    return False


def names_listed_tool(request: str, tools: list[ToolDefinition]) -> bool:
    words = " " + " ".join(tokens(request)) + " "
    for tool in tools:
        parts = tool.name.lower().split("_")
        if tool.name in MEMORY_TOOL_NAMES or len(parts) < 2 or all(part in GENERIC_NAME_WORDS for part in parts):
            continue
        if " " + " ".join(parts) + " " in words:
            return True
    return False


def asks_stored_detail(request: str) -> bool:
    words = tokens(request)
    # A write verb counts where it addresses the assistant, not in the user's account of their own plans ("before I hit send").
    slotted = [word for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip() for part in PART_SPLIT.split(clause) for word in verb_slots(tokens(part))]
    if CODE_IDENTIFIER.search(request.lower()) or any(word in WRITE_VERBS for word in slotted):
        return False
    for clause in CLAUSE_SPLIT.split(request):
        if clause and any(word in SENDING_VERBS for word in verb_slots(tokens(clause))):
            return False
    for index, word in enumerate(words):
        if word in DETAIL_NOUNS and not (word in VERB_LIKE_NOUNS and index and words[index - 1] in VERB_LEADS):
            return True
    return False


def requests_action(request: str) -> bool:
    polite = POLITE_REQUEST.match(request)
    if polite and polite.group(1).lower() in DO_VERBS:
        return True
    causative = CAUSATIVE.match(request)
    if causative and any(word in DO_VERBS for word in tokens(causative.group(1))[1:]):
        return True
    for clause in PART_SPLIT.split(request)[1:]:
        lead = VERB_INITIAL.match(clause)
        if lead and lead.group(1).lower() in EFFECT_VERBS:
            return True
    return False


def classify(request: str, tools: list[ToolDefinition], typo_cues: bool = False, preamble: bool = True, asking: bool = True, anchor: bool = True, lexicon: bool = True, operands: bool = True, save: bool = True) -> Lane:
    read, write = vocabulary(tools)
    cue_text = fold_live_cues(request) if typo_cues else request
    compute = any(tool.name == "run_code" for tool in tools)
    clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
    tails = QUESTION_TAIL.findall(request) if "?" in request else []
    question = asks(request, clauses, asking, tails)
    reason = ""
    acts: list[str] = []
    for clause in clauses:
        words = tokens(clause)
        if preamble and framing_only(clause, words, read, write, lexicon):
            continue
        lead = VERB_INITIAL.match(clause)
        verb = lead.group(1).lower() if lead else ""
        verb_initial = bool(verb) and verb not in NON_VERBS and not clause.strip().endswith("?") and not (asking and QUESTION.match(clause.strip()))
        need = NEED_FORM.search(clause)
        need_verb = need.group(2).lower() if need else ""
        acting = verb if verb in DO_VERBS else (need_verb if need_verb in DO_VERBS else "")
        if acting:
            acts.append(acting if acting != "add" or words[1:2] != ["up"] else "sum")
        if preamble and question and acting in FRAMING_VERBS and not any(word in EFFECT_VERBS or nearest(word, read, lexicon) or nearest(word, write, lexicon) for word in words):
            acting = ""
        if SAVE_FORM.match(clause) or (save and SAVE_FORM_WIDE.match(clause)) or acting:
            reason = reason or "imperative"
        elif verb_initial and any(nearest(word, write, lexicon) for word in words):
            reason = reason or "imperative-setter"
        probes = [word for word in words if not (lexicon and verb_initial and word == verb and word in LOOSE_SYNONYMS)]
        if any(nearest(word, read, lexicon) for word in probes):
            reason = reason or "read-capability"
    if LIVE_CUES.search(cue_text) and not (anchor and record_anchor(request)):
        reason = reason or "live"
    figures = DATE_SPAN.sub(" ", request) if operands else request
    if compute and ARITHMETIC.search(fold_arithmetic_cues(request) if typo_cues else request) and DIGITS.search(figures):
        reason = reason or "arithmetic"
    if names_listed_tool(request, tools):
        reason = reason or "names-tool"
    if reason in STORED_DETAIL_REASONS and asks_stored_detail(request):
        return Lane(RECORDS, "stored-detail")
    if reason == "imperative-setter" and anchor and record_anchor(request) and not effecting(request):
        # A setting-like word beside the user's own record nouns, with nothing to be done, asks about those records.
        return Lane(RECORDS, "record-anchor")
    if reason == "imperative" and question and acts and all(act in TALLY_VERBS for act in acts) and not DIGITS.search(figures):
        # A tally asked over figures the message does not supply is a question about the user's own records.
        return Lane(RECORDS, "stored-figures")
    if reason:
        return Lane(ACTION, reason)
    if requests_action(request):
        return Lane(ACTION, "request")
    if not question and states_own_fact(request):
        return Lane(RECORDS, "statement")
    if question:
        return Lane(RECORDS, "question")
    if asking and tails and not any(REQUEST_FORM.search(tail) for tail in tails):
        return Lane(RECORDS, "asked")
    if asks_stored_detail(request):
        return Lane(RECORDS, "stored-detail")
    if anchor and record_anchor(request):
        return Lane(RECORDS, "record-anchor")
    return Lane(ACTION, "default")


def acting(request: str) -> bool:
    for clause in CLAUSE_SPLIT.split(request):
        if not clause or not clause.strip():
            continue
        for part in PART_SPLIT.split(clause):
            if any(word in DO_VERBS for word in verb_slots(tokens(part))):
                return True
    return False


def unknown_name(request: str, index: UserIndex) -> bool:
    for match in NAME_WORD.finditer(request):
        before = request[: match.start()].rstrip()
        if not before or before[-1] in SENTENCE_BREAK or match.group(0) in SENTENCE_START:
            continue
        if not index.df[index.fix_typo(match.group(0).lower())]:
            return True
    return False


def held_in_records(request: str, tools: list[ToolDefinition], index: UserIndex, anchors: dict[str, tuple[str, float]]) -> bool:
    kinds = {kind for kind, _ in anchors.values()}
    if kinds & NAMED_KINDS or {"k", "b"} <= kinds:
        return True
    read, write = vocabulary(tools)
    for match in POSSESSED.finditer(request):
        phrase = match.group(1).lower().split()
        if any(word in READ_SYNONYMS or nearest(word, read) or nearest(word, write) for word in phrase):
            continue
        noun = next((word for word in phrase if word not in POSSESSION_MODIFIERS), "")
        if len(noun) >= 4 and noun not in STOPWORDS and index.df[noun]:
            return True
    return False


def about_own_records(request: str, tools: list[ToolDefinition], lane: Lane, index: UserIndex, anchors: dict[str, tuple[str, float]]) -> bool:
    if lane.name != ACTION or lane.reason not in OWN_RECORD_CUES or OUTSIDE_SOURCE.search(request):
        return False
    clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
    tails = QUESTION_TAIL.findall(request) if "?" in request else []
    if not asks(request, clauses, True, tails) or acting(request) or unknown_name(request, index):
        return False
    return held_in_records(request, tools, index, anchors)


def own_records_question(request: str, tools: list[ToolDefinition]) -> bool:
    if OUTSIDE_SOURCE.search(request) or names_listed_tool(request, tools) or (fetching(request) and near_reading_tool(request, tools)):
        return False
    clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
    tails = QUESTION_TAIL.findall(request) if "?" in request else []
    return (asks(request, clauses, True, tails) or reading_request(request)) and not effecting(request)


def verb_in(request: str, verbs: frozenset[str]) -> bool:
    for clause in CLAUSE_SPLIT.split(request):
        if not clause or not clause.strip():
            continue
        for part in PART_SPLIT.split(clause):
            if any(word in verbs for word in verb_slots(tokens(part))):
                return True
    return False


def reading_request(request: str) -> bool:
    return verb_in(request, READING_VERBS)


def fetching(request: str) -> bool:
    return verb_in(request, FETCH_VERBS)


def near_reading_tool(request: str, tools: list[ToolDefinition]) -> bool:
    words: dict[str, str] = {}
    for tool in tools:
        if tool.name in MEMORY_TOOL_NAMES or not reads_state(tool.name):
            continue
        for word in tool.name.split("_"):
            if word not in GENERIC_NAME_WORDS and len(word) > 2:
                words[singular(word)] = tool.name
    return any(nearest(word, words) for word in tokens(request))


def effecting(request: str) -> bool:
    return verb_in(request, EFFECT_VERBS)

