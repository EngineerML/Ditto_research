from __future__ import annotations

import re
from dataclasses import dataclass

from .memory.retrieval import SENTENCE_START, STOPWORDS, UserIndex
from .protocol import MEMORY_TOOL_NAMES, ToolDefinition

ACTION = "action"
RECORDS = "records"

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
GENERIC_NAME_WORDS = frozenset("search create set list run execute get file read main chat for team status in save update delete send discover".split())
READ_PREFIXES = ("list_", "search_", "discover_", "read_", "get_", "fetch_", "find_", "lookup_")
READ_SYNONYMS = {"task": "job", "tasks": "job", "queue": "job", "queued": "job", "automatic": "schedule", "scheduled": "schedule", "app": "capabilities", "feature": "capabilities", "features": "capabilities", "option": "capabilities", "options": "capabilities", "setting": "capabilities", "settings": "capabilities", "control": "capabilities", "switch": "capabilities", "help": "capabilities", "calendar": "calendar", "web": "web", "online": "web", "internet": "web"}
DO_VERBS = frozenset("make set change switch use create build run start kick dispatch send email mail schedule put add delete remove forget bin update save search find look pull open read draw generate edit tweak file report check plan split turn spin fetch research see forward pass shoot grab crunch compute normalize calculate take list summarize summarise brighten adjust enable disable move retry try apply execute reason skip describe paint outline talk google browse book crop warm resize convert post launch trigger sort begin proceed handle deploy refactor scrape rework touch bump explain break correct fix write render draft compose confirm verify".split())
FRAMING_VERBS = frozenset("use read look see find search pull open fetch grab take apply list skip google browse research summarize summarise describe explain reason talk compute normalize calculate crunch handle try".split())
NON_VERBS = frozenset("my our i i'm i've we the a an this that these those it its one for on in at when if what which who where how why did do does is are was were will would could can should has have had thanks hey hi ok okay so yes no ditto".split())
LIVE_CUES = re.compile(r"\b(latest|current(?:ly)?|right now|at (?:\w+ )?now|up[- ]to[- ]date|live|online|the web|news|today'?s?|nowadays|these days|changed since|actually changed|what'?s new|out of date|outdated|happening now|going on now)\b", re.I)
ARITHMETIC = re.compile(r"\b(percent|percentage|sum|average|mean|total|times|minus|plus|split|divide|divided|compound|spread|multiply|normalize|fractions?|tip|median|crunch|calc(?:ulation)?)\b", re.I)
DIGITS = re.compile(r"\d")
QUESTION = re.compile(r"\?\s*$|^\s*(?:what|which|who|whom|whose|where|when|how|why|did|do|does|is|are|was|were|will|would|could|can|should|has|have|had)\b", re.I)
CLAUSE_SPLIT = re.compile(r"[;—–]|\s-\s|,\s*(?:and|but|then|so)\s+|\b(?:and then|then)\b|\.\s+|\?\s+")
VERB_INITIAL = re.compile(r"^\s*(?:(?:hey|hi|hello|ok|okay|so|well|thanks|also)\b[,:\-—\s]*)*(?:please\s+|kindly\s+|just\s+|go ahead and\s+|now\s+|actually\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?([a-z]+)\b", re.I)
SAVE_FORM = re.compile(r"^\s*(?:please\s+)?(?:remember|note|keep in mind|bear in mind|make a note|jot down)\s+(?:that|to|this|for later|:)", re.I)
SAVE_FORM_WIDE = re.compile(r"^\s*(?:please\s+)?(?:remember|note|log|record)\s*(?:that|to|this|it|them|for later|:|\.|$)|^\s*(?:please\s+)?(?:keep|bear)\s+(?:that|this|it|them)?\s*in\s+min", re.I)
WANT_WORDS = ("want", "need")
WANT_FORM = re.compile(r"\b(?:i|we)\s+([a-z]+)\s+(?:a|an|the|another)\b(?=(.*))", re.I | re.S)
SAVE_CUE = re.compile(r"\b(?:remember (?:it|this|that)|(?:keep|bear) (?:it |this |that )?in m\w{1,3}|hold onto (?:it|this|that)|for the record|for future reference|note (?:it|this|that)(?: down)?|make a note|note for later|store (?:th\w{1,3}|it)|jot (?:it |this |that )?down)\b", re.I)
NEED_FORM = re.compile(r"\b(i need|i want|i'd like|i would like)\s+(?:you to\s+|it\s+|that\s+|this\s+|the \w+\s+|a \w+\s+)?(\w+)", re.I)
SPEECH_VERBS = frozenset("answer reply respond say state name tell give word phrase".split())
QUESTION_TAIL = re.compile(r"[^.!?]*\?")
NEGATED_OPENER = re.compile(r"^\s*(?:do|does|did|is|are|was|were|will|would|could|can|should|has|have|had)(?:\s+not|n't)\b", re.I)
QUESTION_WORD = re.compile(r"\b(?:what|what'?s|which|who|who'?s|whom|whose|where|where'?s|when|why|how)\b", re.I)
REQUEST_FORM = re.compile(r"\b(?:can|could|would|will|shall)\s+(?:i|you|we)\b", re.I)
RECALL_QUESTION = re.compile(r"\s+me\s+(?:again\s+)?how\s+(?:l\w{1,3}g|m\w{1,3}y|much)\b", re.I)
ADD_UP_ASKED = re.compile(r"^\W*add up\b[^?]*\?", re.I)
# The full stop of an abbreviation that a question mark follows straight away ("Co.?").
ABBREVIATION_ASKED = re.compile(r"(?<=\w)\.(?=\?)")
COMMON_WORDS = frozenset("email emails there their theirs these those where three getting letting reference references planned plans phone phones price prices thing things month months meant means".split())
EFFECT_VERBS = frozenset(word for word in DO_VERBS if word not in FRAMING_VERBS)
READING_VERBS = FRAMING_VERBS | SPEECH_VERBS
FETCH_VERBS = frozenset("search find look fetch pull open grab read research see browse google".split())
RECORD_NOUNS = frozenset("thread account invoice balance record records".split())
DATE_SPAN = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:19|20)\d{2}\b|\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", re.I)

OWN_RECORD_CUES = frozenset({"live"})
DETAIL_NOUNS = frozenset("email emails e-mail address addresses phone phones telephone handle handles username usernames".split())
VERB_LIKE_NOUNS = frozenset("handle handles address email".split())
# Detail nouns also read through a misspelling within one edit (typo handling); real words one edit away are not.
TYPO_DETAIL_NOUNS = frozenset({"handle"})
TYPO_DETAIL_EXCLUDED = frozenset("handled handler handles candle bandle".split())
VERB_LEADS = frozenset("will would can could should to they we i you must".split())
WRITE_VERBS = frozenset("create delete remove clear update change set send forward save add bin forget edit make schedule book put move run start dispatch post cancel rename replace fix define build draft write".split())
# Write verbs also read through a misspelling within one edit (typo handling); real words one edit away are not.
TYPO_WRITE_VERBS = frozenset(verb for verb in WRITE_VERBS if len(verb) >= 5)
TYPO_WRITE_EXCLUDED = frozenset("chance chances charge charges cleat forgot forgotten remote white wrote smart heart stark guild drift refine swatch creche crease".split())
CAPABILITY_QUESTION = re.compile(r"\b(?:what|which)\b[^?.]{0,40}\bcan (?:you|ditto|i)\b[^?.]{0,30}\b(?:you|ditto|here|do|for)\b|\bcan (?:you|ditto) (?:do|help|handle)\b|\bhow (?:do|can|could|would|should) (?:i|you|we)\b[^?.]*\b(?:in here|here|in ditto|in the app|this app|the app)\b|\bis there a way to\b|\bwhat (?:are|do) you (?:able|good|here) (?:to|at|for)\b|\bwhat (?:are|do) you (?:know how to )?do\b", re.I)
POLITE_LEAD = re.compile(r"^\s*(?:(?:hey|hi|hello|ok|okay|so|also|one thing|quick one|real quick|when you can)[,:\-\u2014\s]*)*wh[a-z]{2,3}(?:ever)?\s+you(?:'re|'ve| are| have| get| can)?\s+(?:ready|a sec|a second|a moment|a minute|a chance|around|free|can|get a (?:sec|second|moment|minute|chance)|have a (?:sec|second|moment|minute))[,:\-\u2014\s]+", re.I)
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


def after_polite_lead(request: str) -> str:
    match = POLITE_LEAD.match(request)
    return request[match.end():] if match and request[match.end():].strip() else request


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
    return bool(lead) and within_one_edit(lead.group(1).lower(), "remind") and bool(RECALL_QUESTION.match(request, lead.end()))


def asks(request: str, clauses: list[str], wide: bool, tails: list[str]) -> bool:
    if ABBREVIATION_ASKED.search(request):
        # A question ending on an abbreviation ("... at Acme & Co.?"): its full stop does not end the sentence.
        request = ABBREVIATION_ASKED.sub("", request)
        clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
        tails = QUESTION_TAIL.findall(request)
    if QUESTION.search(request) and not NEGATED_OPENER.match(request):
        return True
    if wide and recall_question(request):
        return True
    if wide and ADD_UP_ASKED.search(request) and not DIGITS.search(DATE_SPAN.sub(" ", request)):
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


def write_verb_typo(word: str) -> bool:
    if len(word) < 5 or word in TYPO_WRITE_EXCLUDED or word in COMMON_WORDS:
        return False
    return any(within_one_edit(word, verb) for verb in TYPO_WRITE_VERBS)


# Writing to a person described or named by a pronoun is reaching them: "I need to write to the current owner; which
# email ..." asks for a detail, not a change.
WRITE_TO = re.compile(r"\bwrite to (?=(?:the|them|him|her|whoever)\b)", re.I)


def reaching(text: str) -> str:
    return WRITE_TO.sub("reach ", text)


def asks_stored_detail(request: str) -> bool:
    words = tokens(request)
    if CODE_IDENTIFIER.search(request.lower()):
        return False
    # A question sentence that asks for a stored detail is one whatever the rest of the message plans to do with it.
    for tail in (QUESTION_TAIL.findall(request) if "?" in request else []):
        tail_words = tokens(reaching(tail))
        if any(word in DETAIL_NOUNS or detail_typo(word) for word in tail_words) and not any(word in SENDING_VERBS or word in WRITE_VERBS or write_verb_typo(word) for word in verb_slots(tail_words)):
            return True
    if any(word in WRITE_VERBS or write_verb_typo(word) for word in words):
        return False
    for clause in CLAUSE_SPLIT.split(request):
        if clause and any(word in SENDING_VERBS for word in verb_slots(tokens(clause))):
            return False
    for index, word in enumerate(words):
        noun = word if word in DETAIL_NOUNS else detail_typo(word)
        if noun and not (noun in VERB_LIKE_NOUNS and index and words[index - 1] in VERB_LEADS):
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


# A balance still owed on something the user's records hold (an invoice, a payment), asked with no figures of its own:
# the figures are in the records, so it is a question about them, whatever the verb.
OWED = re.compile(r"\b(?:outstanding|remaining|remains|still owe|owed?|balance)\b", re.I)
OWED_ON = re.compile(r"\b(?:invoice|payment|paid|inv-[0-9a-z]+)\b", re.I)
FREE_FIGURE = re.compile(r"(?<![\w-])[$£€]?\d[\d,.]*(?![\w-])")


def owes_from_records(request: str) -> bool:
    words = [word.lower() for word in WORD.findall(request)]

    def names(keys: tuple[str, ...]) -> bool:
        return any(word == key or (len(word) >= 5 and within_one_edit(word, key)) for word in words for key in keys)

    owed = bool(OWED.search(request)) or names(("balance", "outstanding", "remaining"))
    held = bool(OWED_ON.search(request)) or names(("payment", "invoice"))
    return owed and held and not FREE_FIGURE.search(request)


def wants_made(request: str, write: dict[str, str], lexicon: bool) -> bool:
    for match in WANT_FORM.finditer(request):
        if any(within_one_edit(match.group(1).lower(), want) for want in WANT_WORDS):
            return any(nearest(word, write, lexicon) for word in tokens(match.group(2)))
    return False


PASS_VERBS = ("send", "sent", "forward")
PASS_NOT = frozenset("spend spent seen seed sand lend lent rent tent bend bent vent went sens".split())
MAIL_VERB = re.compile(r"\be-?mail\s+(?:it|that|this|them|what|the\s+\w+)\b", re.I)
PASS_PHRASE = re.compile(r"\b(?:pass|get)\s+(?:it|that|this|the\s+\w+)\s+(\w+)\b", re.I)
TO_NAME = re.compile(r"\bto\s+[A-Z][a-z]+\b")


def pass_verb(word: str) -> bool:
    word = word.lower()
    if word in PASS_NOT:
        return False
    return (any(word == verb or (len(word) >= 4 and within_one_edit(word, verb)) for verb in PASS_VERBS) or word.startswith("forw")
            or re.fullmatch(r"f[a-z]{1,3}ward", word) is not None)


def passes_on(request: str) -> bool:
    """A request to send, forward or email something on to a person it names: a send-type verb (read through one-edit
    slips), "email it", or "pass it along" / "get it over" within the few words before "to <Name>"."""
    for match in TO_NAME.finditer(request):
        before = request[max(0, match.start() - 60):match.start()]
        if MAIL_VERB.search(before) or any(within_one_edit(m.group(1).lower(), w) for m in PASS_PHRASE.finditer(before) for w in ("along", "over")):
            return True
        if any(pass_verb(word) for word in re.findall(r"[A-Za-z][A-Za-z\-]*", before)[-5:]):
            return True
    return False


LOOKUP_LEAD = re.compile(r"^\W*(?:(?:hey|ok|okay|so|quick one|one thing)\W+)*(?:l\w{1,3}k (?:this|it|that) up|search (?:for|the web)|google)\b", re.I)


def classify(request: str, tools: list[ToolDefinition], typo_cues: bool = False, preamble: bool = True, asking: bool = True, anchor: bool = True, lexicon: bool = True, operands: bool = True, save: bool = True) -> Lane:
    read, write = vocabulary(tools)
    if typo_cues:
        request = after_polite_lead(request)
    cue_text = fold_live_cues(request) if typo_cues else request
    compute = any(tool.name == "run_code" for tool in tools)
    clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
    tails = QUESTION_TAIL.findall(request) if "?" in request else []
    question = asks(request, clauses, asking, tails)
    if asking and ADD_UP_ASKED.search(request) and not DIGITS.search(DATE_SPAN.sub(" ", request)):
        return Lane(RECORDS, "asked")
    if passes_on(request) and not states_own_fact(request):
        return Lane(ACTION, "request")
    if LOOKUP_LEAD.search(request):
        return Lane(ACTION, "look-up")
    reason = ""
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
    if reason == "arithmetic" and owes_from_records(request):
        return Lane(RECORDS, "stored-figure")
    if reason in STORED_DETAIL_REASONS and asks_stored_detail(request):
        return Lane(RECORDS, "stored-detail")
    if reason:
        return Lane(ACTION, reason)
    if requests_action(request):
        return Lane(RECORDS, "stored-figure") if owes_from_records(request) else Lane(ACTION, "request")
    if not question and SAVE_CUE.search(request):
        return Lane(ACTION, "request")
    if not question and wants_made(request, write, lexicon):
        return Lane(ACTION, "request")
    if not question and states_own_fact(request):
        return Lane(RECORDS, "statement")
    if question and "capabilities" in read.values() and CAPABILITY_QUESTION.search(request) and not OUTSIDE_SOURCE.search(request):
        return Lane(ACTION, "capability-question")
    if question:
        return Lane(RECORDS, "question")
    if asking and tails and not any(REQUEST_FORM.search(tail) for tail in tails):
        return Lane(RECORDS, "asked")
    if asks_stored_detail(request):
        return Lane(RECORDS, "stored-detail")
    if owes_from_records(request):
        return Lane(RECORDS, "stored-figure")
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


def names_held_alias(request: str, tools: list[ToolDefinition], index: UserIndex, aliases: set[str]) -> bool:
    if OUTSIDE_SOURCE.search(request) or names_listed_tool(request, tools) or fetching(request) or unknown_name(request, index):
        return False
    return any(re.search(r"\b" + re.escape(alias) + r"\b", request) for alias in aliases)


def own_records_question(request: str, tools: list[ToolDefinition], held: bool = False) -> bool:
    """A question about the user's own records. With held (the request names an identifier the user's own records carry),
    a reading verb next to a word near a reading tool's name does not make it a tool request."""
    if OUTSIDE_SOURCE.search(request) or names_listed_tool(request, tools) or (not held and fetching(request) and near_reading_tool(request, tools)):
        return False
    clauses = [clause for clause in CLAUSE_SPLIT.split(request) if clause and clause.strip()] or [request]
    tails = QUESTION_TAIL.findall(request) if "?" in request else []
    return (asks(request, clauses, True, tails) or reading_request(request)) and not effecting(request)


# "Put <them> in order": arranging the things named in the reply, which changes nothing, read as listing them.
ARRANGING = re.compile(r"\bput\s+([^.?!]{1,60}?)\s+in\s+(?:order|sequence)\b", re.I)


def within_records(request: str, tools: list[ToolDefinition]) -> bool:
    """The own-records question's guards without its asking test: no outside source, no listed tool named, no fetch near
    a listed reading tool's words, and no change asked for."""
    if OUTSIDE_SOURCE.search(request) or names_listed_tool(request, tools) or (fetching(request) and near_reading_tool(request, tools)):
        return False
    return not effecting(ARRANGING.sub(r"list \1", request))


def verb_in(request: str, verbs: frozenset[str]) -> bool:
    for clause in CLAUSE_SPLIT.split(request):
        if not clause or not clause.strip():
            continue
        for part in PART_SPLIT.split(clause):
            if any(word in verbs for word in verb_slots(tokens(part))):
                return True
    return False


# Real English words one edit from a reading verb, read as themselves (gen_readslips.py, starter-kit WordPiece vocabulary).
READ_SLIP_REAL = frozenset("answers apple arab bell bind book bread browne brows browser bull cake calculated came candle cell compete computed computer cook cord crab dame dead dell described describes dive dread dull estate explains fake fame fell finds fine fined finn fins fist fitch five fond ford full fund game gave given gives grabs graf gram gran gray graz handel handled handler handles head hell hind hive hook hull jake kind lake lame last lead lest lift lisa lists liszt live lock looks loop lord lost lust make mead mind mist named names nape nate nave nell nord null opens oven owen phase phrases pill poll pulls pulp rake reads ready real rear reasons reed reid rely repay replay responds road rook sake same season sell ship skate skin slate slip stade stage stake stale stalk stare stat stated staten states stats statue summarized sword tack taken takes tale talks tall taluk tame tank tape task tate tells till toll took tread treason wake walk ward well wind wood words wore work world worm worn yell".split())
READ_SLIP_VERBS = tuple(sorted(verb for verb in READING_VERBS if len(verb) >= 4))


def reading_slip(request: str) -> bool:
    """A clause opening with "track down", or with a reading verb misspelt within one edit (not a real English word)."""
    for clause in CLAUSE_SPLIT.split(request):
        if not clause or not clause.strip():
            continue
        for part in PART_SPLIT.split(clause):
            words = tokens(part)
            for index, word in enumerate(words):
                if index and words[index - 1] not in VERB_SLOT_LEADS:
                    continue
                after = words[index + 1] if index + 1 < len(words) else ""
                if within_one_edit(word, "track") and within_one_edit(after, "down"):
                    return True
                if len(word) < 4 or word in READING_VERBS or word in READ_SLIP_REAL or word in COMMON_WORDS:
                    continue
                if len([verb for verb in READ_SLIP_VERBS if within_one_edit(word, verb)]) == 1:
                    return True
    return False


def reading_request(request: str) -> bool:
    return verb_in(request, READING_VERBS) or reading_slip(request)


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
    return verb_in(reaching(request), EFFECT_VERBS)


def detail_typo(word: str) -> str:
    if len(word) < 5 or word in TYPO_DETAIL_EXCLUDED or word in COMMON_WORDS:
        return ""
    return next((noun for noun in TYPO_DETAIL_NOUNS if within_one_edit(word, noun)), "")
