"""Answer-form hints routed by question type (policy v13 I5 clarification on routed instruction guidance: a router may
pick advisory guidance by the request's phrasing or answer form). Copied into app/ as qtype.py by patch_qtype.py.

A question about one of the user's threads is classified by its wording, read through one-edit misspellings, into
the kind of answer it asks for; the deciding call then sees one advisory line naming that answer form. The host
answers nothing and acts on nothing. Questions over a named case file or an entity id get no hint."""
from __future__ import annotations

import re

WORD = re.compile(r"[A-Za-z][A-Za-z']*")
KEYWORDS = frozenset(
    "whose whoever owner holds holding holder running actually accountable responsible thread person "
    "status state stand standing landed position latest where with "
    "next action waiting happen pending carries through channel means comes handle "
    "lesson takeaway learn resolve remember advice wrapped "
    "email address current present signal handle balance remains remaining outstanding payment owed "
    "figure change length altogether total stood partial invoice long many "
    "agree disagree disagreement consistent "
    "order sequence original replacement replaced earliest oldest newest first second".split()
)
COMMON = frozenset("these those there their which while whole would could should stats when what".split())


def one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def folded(text: str) -> str:
    """The text, lower-cased, with each word of four or more letters that is one edit off exactly one keyword read as it."""
    def snap(match: re.Match) -> str:
        word = match.group(0).lower()
        if len(word) < 4 or word in KEYWORDS or word in COMMON:
            return word
        near = [key for key in KEYWORDS if one_edit(word, key)]
        return near.pop() if len(near) == 1 else word
    return WORD.sub(snap, text)


# Questions naming a long code (a case file, an entity id): the release's generic identifier shape, plus entity ids.
PROGRAM = re.compile(r"\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b|\bentity-[0-9a-f]", re.I)
HOST_NOTE = "Host note (advisory, from the assistant's software, not from the user; the message and the records decide):"
ASKED = re.compile(r"(?<=[.?!])\s+")
DISAGREE = re.compile(r"\b(disagree\w*|clash\w*|line up|lines up|agree\w*|consistent|match|each record|all of t\w{1,3}m|sources|different things|say different|as far as the records go)\b")
EMAIL = re.compile(r"\b(email|e-mail|work address|address|work a\w{2,6}s)\b")
OWNER = re.compile(
    r"\b(whose is|who owns|whoever \w+ it now|who \w{2,4} it now|who is (?:actually )?\w+ it now|who ended up|who is accountable"
    r"|accountable for it|who has (?:it|the \w+)(?: now)?|who holds|who is (?:on point|responsible)|who do i chase|current owner"
    r"|the owner|as the owner|present owner|has it now|owns it|holding it|holds it|running it|the person \w+ for it now"
    r"|who o\w{1,3}s it|w\w{3,6}r o\w{1,3}s it|who is on p\w{2,4}t for it|who is [ra]\w{6,12}e for it|who e\w{2,4}d up|as the o\w{2,4}r"
    r"|the person h\w{2,6}g it now|p\w{3,6}t owner|current ow\w{0,2}r)\b"
)
NEXT = re.compile(
    r"\b(next (?:action|step|move)|doing what next|act next|comes next|the next move|open action|\w+ action and who carries it"
    r"|who carries it|waiting to happen|to happen, who is on it|has the ball|owes the next|mean\w to act|who is d\w{1,5} what n\w{1,3}t|by what m\w{2,5}|who is on it,? and how|and through what|who c\w{2,6}s it|who d\w{2,4} what|pending a\w{2,6}n|waiting to h\w{2,5}n|n\w{1,3}t (?:a\w{2,6}n|s\w{1,3}p|m\w{1,3}e)|who has the b\w{1,3}l|what do th\w{1,3} n\w{1,3}d to do|o\w{2,3}n a\w{2,6}n, who has it|who has it, and how will)\b"
)
STATUS = re.compile(
    r"\b(where does it stand|stands? right now|what state|state of (?:play|it|p\w{1,3})|current position|where it landed"
    r"|where did it (?:end up|land\w*|\w+ up)|its status|status now|what is its st\w* now|the state is|latest on where"
    r"|current standing|where are we with it"
    r"|what is its st?\w{1,4}s now|the current st?\w{3,7}g of it|current p\w{4,7}n on it|where d\w{1,3} it st\w{1,3}d"
    r"|where it l\w{2,5}|where are we w\w{1,3} it|state of p\w{1,4})\b"
)
LESSON = re.compile(
    r"\b(lesson|takeaway|take away|took away|teach|taught|moral|rule did i set|what did i learn|resolve to do"
    r"|remember next time|advice i kept|stuck with me|did i note when it wrapped|when it wrapped"
    r"|what was the a\w{2,7} i k\w{1,3}t|r\w{1,3}e did i set|what was the m\w{3} i r|s\w{2,4}k w\w{1,3} me"
    r"|did the m\w{1,3} t\w{2,4}h me|remember n\w{1,3}t t\w{2,4}|t\w{2,3}e a\w{1,4}y from|r\w{3,6}e to do d\w{6,10}y"
    r"|l\w{2,4}n i wrote|l\w{2,4}n did i note|when it w\w{3,5}d)\b"
)

ASOF = re.compile(r"\b(as of (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|as (?:they|it) stood on|as it stood|current on (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|dated? (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|^\W*on (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w* \d|on that date|d\w{1,3}d (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|as t\w{1,3} st\w{1,3}d on)")
HANDLE = re.compile(r"\bsignal\b")
BALANCE = re.compile(r"\b(still owe\w*|owed|balance|remains|remaining|outstanding)\b")
PAYMENT = re.compile(r"\b(payment|paid|pay|partial|invoice|p[a-z]{2,4}ial|p[a-z]{1,3}m[a-z]{1,2}n?t)\b")
PLACE_DAYS = re.compile(r"\b([Hh]ow m\w{2,4} days (?:did|do|are|were|is|was) (?:we|it|our)\b.* in (?:the )?[A-Z]|how long was the [A-Z]\w+ stay|days (?:in|is the) (?:the )?[A-Z]|(?:the )?changed [A-Z]\w+ (?:stay|part|leg|p\w{0,2}rt|prat|s\w{1,3}y)\b|s\w{1,3}y in (?:the )?[A-Z]|had us in (?:the )?[A-Z]|the [A-Z]\w+ (?:part|stay|leg|p\w{0,2}rt|prat|s\w{1,3}y)\b)")
TRIP_LENGTH = re.compile(r"\b(full length|full len\w+|how long is the trip|(?:whole|wgole|entire) trip|trip altogether|altogether now|how long [\w ]{1,30} is now|length of|how many days is (?!the chang)[\w ]{1,40} now"
                         r"|add up the current l\w{1,3}s|f\w{1,3} l\w{2,5}h of|how m\w{1,3}y days in total|w\w{2,4}e trip now|how m\w{1,3}y days is (?!the chang)[\w ]{1,40} now)\b")
QUANTITY = re.compile(r"\b(figure (?:come|cmoe|comme|comes)|work out to|after the change described|apply the stated change|total now|resulting \w+ amount|final \w+ figure|arrive at|figure after the change|once you apply|follow the notes|what are the \w+ now"
                      r"|figure l\w{1,3}d after|after the a\w{4,9}t th\w{0,3} s\w{3,6}d out|t\w{2,3}e the s\w{2,4}d? change|after the change t\w{1,4} d\w{4,8}d"
                      r"|resul\w{2,5}g \w+ amount|current \w+ n\w{3,5}r once|once you a\w{1,4}y|figure c\w{2,4}e to|w\w{1,3}k out to|following the o\w{5,9}n in the notes)\b")
# A question asking in what order things held a role: an explicit order or sequence, a first-to-last span, or the first
# one set against the one after it (which came first and which replaced it, the original and its replacement, who we
# started with and who took over). "In order to" is a purpose, not an order.
HINTS = {
    "direction": "What this asks for: whether it went up, down or stayed the same, as one of increase, decrease or unchanged, then the figure asked for, the two separated by ' ; ' on the ANSWER line.",
    "asof": "What this asks for: the value as the records stood on that date: the latest record dated on or before it, even when a later record changed it. A record dated after that date can still tell you which trip, project or person the message means (a name given to it later); only the value is read as it stood on that date.",
    "handle": "Give the handle only if it is still on record. If a later note says the handle itself was dropped, removed, retired or closed, reply that you no longer have a Signal handle on record for them because it was removed, naming them by the nickname and the workplace the notes give, and do not give the old one. A note that only tidies or reconciles another of their details (an address or an email) leaves the handle on record.",
    "balance": "Work it out only from amounts the notes give, and give only the resulting balance. If an amount it needs is mentioned but never given, such as a payment with no figure, say you have no record of that amount and, in the ANSWER line itself, name the record the notes say holds it, as the notes call it (for example 'ANSWER: no record of the partial payment amount; it is in the bank export, which the notes do not give'), without asking for it, estimating it or quoting the other amounts.",
    "place-days": "If the notes never show the trip going to that place, the answer is not a number (not 0 days): say no record shows the trip going there and name the places it did go, without their days, and put that on the ANSWER line too. Otherwise give the days spent there after every change the notes record.",
    "trip-length": "What this asks for: the trip's total days now, after every change the notes record to the original plan, given alone as one number of days: leave the days of each stay out of the reply and the ANSWER line.",
    "quantity": "What this asks for: the value after applying the change the thread describes to where it started, with its unit. A corrected figure replaces the earlier one. When a note itself says what part of a figure is left over or still open, that part, as the note describes it, is the value asked for. So when the message asks for a money figure and a note approves an amount up to a limit and says how much of it is already spent, taken up or spoken for, the figure is what is still open: the limit less that part, not the limit itself. A note that only delays it moves its dates, not the figure. Work any sum or difference out with the calculate tool, not in your head, and write a money figure with both decimal places (1250.50, not 1250.5).",
    "owner-email": "What this asks for: the person who holds it now, after every handover the notes record (a person, not an organisation or company), and then that person's current work email from the latest note about them, which may name them by a nickname the notes give them: the one the notes give for the employer they are at now, an address from before they moved being out of date, and an address a note gives for the thread or project itself (a shared desk or team inbox) not being theirs. Only a handover moves it: a note that hands or passes the thing itself to someone, says it is theirs now, or says the previous holder is off it or stepped back. A company, supplier, venue or provider the work moved to, even one a note says took it over or has it now, supplies it and does not hold it: the holder is a person. A person who agreed to do a task on it, holds an open action, the next step or the ball, or is being waited on does not become its holder for that. The person the user files the thread under (the friend or relative it started with or came up with) is not its holder unless a note hands it to them. Every thread has a holder: when no note hands it on, the person the notes put in charge of it at the start still holds it, so give that person rather than saying no one holds it.",
    "owner": "What this asks for: the full name of the one person who holds it now, after every handover the notes record: a person, not a status, a date, an amount, a place or an organisation. When the question says which records to go by, the owner is the one those records state, even where notes about a thread with a similar name hand it to someone else. Only a handover moves it: a note that hands or passes the thing itself to someone, says it is theirs now, or says the previous holder is off it or stepped back. A company, supplier, venue or provider the work moved to, even one a note says took it over or has it now, supplies it and does not hold it: the holder is a person. A person who agreed to do a task on it, holds an open action, the next step or the ball, or is being waited on does not become its holder for that. The person the user files the thread under (the friend or relative it started with or came up with) is not its holder unless a note hands it to them. Every thread has a holder: when no note hands it on, the person the notes put in charge of it at the start still holds it, so give that person rather than saying no one holds it.",
    "next": "What this asks for: the one person who acts next, the task they will do, and the channel they will use (in person, chat, email, phone and the like), from the latest note that sets the next step, which may be a follow-up or a handover giving the new holder's opening action; within one note the later passage holds, a later follow-up replaces the next action that came with a handover, and whoever holds the work is not always the one with the next step. End with the ANSWER line holding exactly those three parts, a few words each, as person ; task ; channel (for example 'Dana Reyes ; book the site visit ; email'): the task as a short verb phrase spelled correctly, with no dates, reasons or second task.",
    "status": "What this asks for: the state the latest note that says where it stands puts it in, in the note's own words for that state, whatever words the note uses (such as set, confirmed, rebooked, postponed, completed or on hold), all of them (on hold, not hold) and nothing after them (not what it still waits on): not a place, a person, a task someone owes, a reference code or the history, and not a word the question itself uses (where it landed, where it stands, its position): give the note's words, spelled correctly. Every thread has a latest state; give it rather than saying there is none.",
    "lesson": "What this asks for: the lesson or rule the notes record for it, in the notes' own words.",
    "order": "What this asks for: the ones that filled the role the question names, in the order they held it, from the earliest to the latest, each one that took it over or replaced it, as the notes record the change. Give each by the name the notes give it (a company, venue, supplier or service when the role is one), not the people who hold, run or follow the thread. End with the ANSWER line listing them in that order, separated by ' ; ' (earliest ; the one that replaced it).",
    "disagree": "What this asks for: where it stands according to each note that says so (the latest state the notes give, and any different state another note or record gives for it) and whether they agree. A state is where it stands (such as set, confirmed, rebooked, postponed, completed or on hold), not who holds it, a task someone owes or a change to its details. When notes give different states, give each state in the notes' own words and say the notes disagree, putting each state and the word disagree on the ANSWER line, separated by ' ; '. When every note gives the same state, give it and say they agree.",
}


def asked_part(message: str) -> str:
    """The last sentence of the message that asks something, else the whole message."""
    parts = [part for part in ASKED.split(message.strip()) if part.strip()]
    asking = [part for part in parts if "?" in part]
    return asking.pop() if asking else message


DIRECTION = re.compile(r"\br\w{3,5},?\s+l\w{3,5},?\s+or\s+l\w{2,4}\b")
ORDER = re.compile(
    r"\b(in (?:what|which) order|in order(?! to\b)|in the order (?:t\w{0,3}y|it|that|of|in which)|(?:what|which) order (?:did|do|were|was|are)"
    r"|(?:the )?sequence of|the s\w{0,2}q\w{2,6}e of|chronological\w*|(?:earliest|oldest) (?:first|to (?:newest|latest|last))|o\w{1,6} to newest"
    r"|first\b[^?.!]{0,40}\b(?:second|replaced|replacement|then s\w{3,6}d|t\w{1,3}k over)"
    r"|original\b[^?.!]{0,40}\b(?:replaced|replacement|then|and w\w{2,4}h (?:is|was))"
    r"|start\w* w\w{1,3}h\b[^?.!]{0,60}\bt\w{1,3}k over)\b"
)



def last_part(message: str) -> str:
    """The message's last sentence."""
    parts = [part for part in ASKED.split(message.strip()) if part.strip()]
    return parts[-1] if parts else message


def question_kind(message: str) -> str:
    from .thint import own_setting
    if own_setting(message) == "asked":
        return "own-setting"
    if PROGRAM.search(message):
        return ""
    whole = folded(message)
    if ASOF.search(whole):
        return "asof"
    if HANDLE.search(whole):
        return "handle"
    if BALANCE.search(whole) and PAYMENT.search(whole):
        return "balance"
    if TRIP_LENGTH.search(whole):
        return "trip-length"
    if PLACE_DAYS.search(message) and re.search(r"\b(?:days?|how l\w{0,3}g)\b", whole):
        return "place-days"
    for text in dict.fromkeys((folded(asked_part(message)), folded(last_part(message)))):
        kind = asked_kind(text, whole)
        if kind:
            return kind
    return ""


def asked_kind(text: str, whole: str) -> str:
    if DISAGREE.search(whole) and (STATUS.search(whole) or re.search(r"\b(?:status|state|position|stand\w*|landed|land)\b", whole)):
        return "disagree"
    if DIRECTION.search(whole) and re.search(r"\b(?:raise|lower|leave)\w*\b", whole):
        return "direction"
    if EMAIL.search(text) and OWNER.search(text):
        return "owner-email"
    if NEXT.search(text):
        return "next"
    if OWNER.search(text):
        return "owner"
    if STATUS.search(text):
        return "status"
    if LESSON.search(text):
        return "lesson"
    if QUANTITY.search(text):
        return "quantity"
    if ORDER.search(text):
        return "order"
    return ""


def answer_hint(message: str) -> str:
    kind = question_kind(message)
    if kind == "own-setting":
        from .thint import own_setting_asked_hint
        hint = own_setting_asked_hint(message)
    else:
        hint = HINTS.get(kind, "")
    return f"{HOST_NOTE} {hint}" if hint else ""


def without_host_note(text: str) -> str:
    """The text before any appended host note: what the user and the records said."""
    at = text.find("\n\n" + HOST_NOTE)
    return text if at < 0 else text[:at]
