"""Request-routed tool hints (policy v13 I5 clarification on routed instruction guidance: a router may pick advisory
guidance by the request's phrasing or the tool family). Copied into app/ as thint.py by patch_thint.py.

A request to the action lane is matched, through one-edit misspellings of a fixed keyword list, against a few kinds
of request; for the earliest kind in a fixed order that matches, one advisory line is appended after the message. The deciding model
still sees the request, the records and the whole catalog, and makes every call; the host acts on nothing."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .lane import after_polite_lead, passes_on
from .typofold import DECOY_WORDS, FOLD_WORDS, REAL_WORDS

WORD = re.compile(r"[A-Za-z][A-Za-z']*")
KEYWORDS = frozenset(
    "agreed settled decided landed decision exactly already "
    "reasoning thinking effort depth usual normally normal "
    "handoff scratchpad reviewer reviewers "
    "workflow workflows existing exists create formal "
    "sandbox routine checksum evaluate execute "
    "picture image photo brightness "
    "planning context update".split()
)
COMMON = frozenset("these those there their which while would could should about".split())
GENERIC_PARTS = frozenset(
    "run search set create list discover delete update save fetch file gmail calendar edit execute read artifacts code web "
    "memories memory subjects subject tools tool chat workflow workflows schedules job jobs agent capabilities image links "
    "effort reasoning accent color font theme preferences feedback team events event in for main send".split()
)


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
    """The text, lower-cased, with each slip one edit off exactly one pattern word read as it (real words stay)."""
    def snap(match: re.Match) -> str:
        word = match.group(0).lower()
        if len(word) < 4 or word in FOLD_WORDS or word in REAL_WORDS or word in COMMON:
            return word
        if text[match.start() - 1:match.start()] == "-" or text[match.end():match.end() + 1] == "-":
            return word
        near = [key for key in FOLD_WORDS if one_edit(word, key)]
        near = [key for key in near if not (key.endswith("s") and key[:-1] in near)]
        if len(near) != 1 or any(one_edit(word, decoy) for decoy in DECOY_WORDS) or any(one_edit(word, common) for common in COMMON):
            return word
        return near.pop()
    return WORD.sub(snap, text)


AGREED = re.compile(r"\b(the way we (?:already )?(?:agreed|settled|decided|a\w{3,5}d)|what we d\w{1,6}d (?:together|t\w{3,8}r)|f\w{5,8}g what we d\w{1,6}d|what we (?:settled|landed|decided|agreed)(?: on)?|as we (?:settled|agreed|decided)|per what we|following what we decided|exactly as we)\b")
# A request naming a long code (a planning context): the release's generic identifier shape.
PLANNING = re.compile(r"\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b")
HOST_NOTE = "Host note (advisory, from the assistant's software, not from the user; the message and the records decide):"
LOOKUP = re.compile(r"\b(look up|lookup|pull|check|find|latest|current|reading|figure|research|search)\b")
WEEKDAY = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")
ASKS = re.compile(r"\?|^\W*(?:when|which|what|who|where|how)\b")
SENDING = re.compile(r"\b(send|email|e-mail|shoot|fire off|get back to|over to|forward|mail|get b\w{2,3}k to|get (?:th\w{1,2}m|t\w?em) out to|get (?:th\w{1,2}m|t\w?em) (?:the|my)|get the [\w ]{1,60}? to (?:th\w{1,2}m|t\w?em)|s\w{2,3}t (?:th\w{1,2}m|t\w?em)|f\w{2,3}e off)\b")
EFFORT = re.compile(r"\b(reasoning|thinking|how hard you think|how deeply)\b")
HANDOFF = re.compile(r"\b(handoff|scratchpad)\b")
WORKFLOW_CHECK = re.compile(r"\b(existing (?:workflow|w[a-z]{2,4}f[a-z]{1,3}w)|(?:workflow|w[a-z]{2,4}f[a-z]{1,3}w) exists|already have a (?:workflow|w[a-z]{2,4}f[a-z]{1,3}w)|see if a (?:workflow|w[a-z]{2,4}f[a-z]{1,3}w)|look for an? \w+ (?:workflow|w[a-z]{2,4}f[a-z]{1,3}w)|whether i already have|already h\w{1,3}e an? (?:workflow|w[a-z]{2,4}f[a-z]{1,3}w))\b")
WORKFLOW_CREATE = re.compile(r"\b(if not|if it'?s missing|if none|if there isn'?t|if t\w{1,4}e isn'?t|create one|make one|set one up)\b")
HOW_TO = re.compile(r"^\W*(?:(?:hey|hi|ok|okay|so|quick one|one thing|oh right|w\w{2,3} you get a sec)\W+)*(?:how (?:do|can|could) i\b|is th[a-z]{2,4} a way\b|can i\b)")
EARLIER_IMAGE = re.compile(r"\b(?:(?:image|picture|photo|render|i\w{2,4}e) from earlier|(?:that|the) latest r\w{3,5}r|the one you (?:just )?made|you (?:just )?made|from before|the last (?:image|picture|photo)|that picture|the picture you|the image you)\b")
# A question about how to reach or contact a person asks for a stored detail, not how to use Ditto.
CONTACT_ASK = re.compile(r"\b(?:reach|contact|get hold of|get in touch with|message|text|call|email)\b")
SANDBOX = re.compile(r"\bsandbox\b|\bcode mode\b|\bin-process\b|\bchecksum\b|\bsa[a-z]{1,3}box\b|\bcode m[a-z]{1,2}e\b")
SAVE_CUE = re.compile(r"\b(?:remember (?:it|this|that)|(?:keep|bear) (?:it |this |that )?in m\w{1,3}|hold onto (?:it|this|that)|for the record|for future reference|note (?:it|this|that)(?: down)?|make a note|note for later|store (?:th\w{1,3}|it)|jot (?:it |this |that )?down)\b", re.I)
CAPABILITY_ASK = re.compile(r"\b(?:what (?:kinds? of )?(?:things|stuff) (?:can|could) (?:i|you)|what (?:can|could) (?:you|this (?:app|assistant)|ditto) (?:actually )?(?:do|help)|what (?:you|this (?:app|assistant)) (?:can|is able to|are able to) (?:actually )?(?:do|help)|what (?:you are|this (?:app|assistant) is) capable of|where (?:do|can) i find|what options do you have|what (?:a\w{6,9}s|features) do you have|what k\w{2,4}s of things can i"
    r"|w\w{2,4}e do i find|walk me through what|break down what (?:this|the) (?:app|assistant)|a sense of what (?:this|the) (?:app|assistant))\b")
WORKFLOW_NEW = re.compile(r"\bworkflows?\b|\bw[a-z]{2,4}f[a-z]{1,3}ws?\b")
NEW_SAVED = re.compile(r"\b(?:into|as) a\s+(?:new\s+)?saved\b|\bas a (?:multi-step )?workflow\b|\bmake\b[^.?!]{0,80}\ba saved workflow\b|\bd\w{2,4}e a saved workflow\b")
MAKE_VERB = re.compile(r"\b(?:create|make|design|build|put together|set up|turn|want|need|save|define)\b")
JOB_GO = re.compile(r"\b(?:not a plan|the real thing|don'?t (?:just )?(?:tell|show) me how|i want it done|no walkthrough|kick it off|start it|begin|get going|go ahead and|please actually|start working on|asynchronously|send an agent|have a worker|in the background)\b")
JOB_WORK = re.compile(r"\b(?:build|refactor|scaffold|scrape|convert|write|add|set up|deploy|summari[sz]e|fix|migrate|generate)\b")
JOB_NOT = re.compile(r"\b(?:arithmetic|compute|calculation|percent|don'?t build|no need to spin|not a coding job)\b")
SCHEDULE_TOPIC = re.compile(r"\b(?:on repeat|on a timer|on a cadence|timed runs?|recurring runs?|automatic runs?|hands-off runs?|(?:go|kick off|start|run|trigger|fire) on their own|on th\w{2,3} own|r\w{2}u\w{2,4}g runs?|hands-off r\w{0,2}ns?|(?:queued|set|lined up|due) to run|workflow schedules|schedules on my workflows|automatically right now)\b")
SCHEDULE_ASK = re.compile(r"\b(?:what|which|wh[a-z]ch|show|lay out|remind me|pull up|check|look at|list|tell me|run down)\b")
TOOL_LOOKUP = re.compile(r"\b(?:search your tools|which of your tools|what tool would you use|right tool binding)\b")
STATED_ARITHMETIC = re.compile(r"\b(?:what percent of|compound total|to sum to 1|just compute|crunch this|quick calculation|help me work this out|help me work t\w{1,3} out|c\w{2,5}h t\w{1,3} for me|quick c\w{6,10}n|just do the arithmetic|one-off calculation)\b")
TEAM_FEEDBACK = re.compile(r"\b(?:let the team know|for the (?:ditto )?team|to the (?:ditto )?team|to the devs|for the product folks|whoever builds this|as feedback|file feedback|bit of feedback|something to log)\b")
COLOUR_MODE_SET = re.compile(r"\b(?:for the whole app|make the app (?:dark|light)|switch the app over to the (?:dark|light)|(?:light or dark|dark or light)\b[^.]{0,30}\b(?:device|system setting)|(?:mirror|follow|track|match|sync)\b[^.]{0,30}\b(?:my system setting|whatever my device|to my device))")
SEARCH_THEN_READ = re.compile(r"\b(?:search|look up|web search|find a page)\b[^.]{0,80}\b(?:read it|read the (?:top|first|best|leading) (?:page|result|hit|source)|open the (?:top|first|best|leading) (?:result|hit|page|link)|boil down|recap|gist of)\b")
EFFORT_ANY = re.compile(r"\b(?:reasoning|thinking|effort|how hard you think|how deeply|how much you reason|depth|think (?:hard|harder|deeply|carefully|everything through)|reason (?:as )?(?:deeply|carefully)|go as deep as you can|overthink\w*|deliberat\w*|as thorough and careful as)\b")
EFFORT_USUAL = re.compile(r"\b(?:usual|normally|normal|what i (?:like|want|prefer)|my default|how i like|the way i like)\b")
EFFORT_LEVEL = re.compile(r"\b(?:hard|harder|carefully|careful|deep|deeply|thorough|thoroughly|moderate|balanced|middle|medium|quick|light|lighter|lightest|minimal|low|high|max|maximum|snappy|fast|overthink\w*|take your time)\b")
# The effort setting by name, and the lead-ins before a request, neither of which states a level.
EFFORT_SETTING = re.compile(r"\b(?:reasoning effort|effort level|how hard you think|thinking level|reasoning depth|reasoning level|thinking depth)\b")
EFFORT_LEAD = re.compile(r"^\W*(?:(?:hey|ok|okay|so|one thing|quick one|when you get a sec)\b\W*)+")


def effort_stated(text: str) -> str:
    """The text without its lead-in or the setting's own name, so any level word left is one the message states."""
    return EFFORT_SETTING.sub(" ", EFFORT_LEAD.sub(" ", text))
PENDING_REF = re.compile(r"\b(?:it|that|this)\b")
DELETE_ONE = re.compile(r"\b(?:clear|drop|bin|delete|remove|clean up|can go|is stale|stale now|get rid of|toss)\b")
ONE_NOTE = re.compile(r"\b(?:note|receipt|entry|scratch\w*|throwaway|thr\w*away)\b")
KEEP_REST = re.compile(r"\b(?:keep|stays?|not to be touched|nothing else|just that|only that|leave)\b")
JOB_WORDS = re.compile(r"\b(?:jobs?|worker|background|asynchron\w*)\b")
ARTIFACT_ASK = re.compile(r"\b(?:build|make|create|put together|design|code|whip up|generate|m\w{2,3}k up)\s+(?:me\s+)?(?:a|an)\b[^.?!]{0,50}\b(?:apps?|games?|pages?|trackers?|timers?|resumes?|dashboards?|calculators?|websites?|sites?|quiz|planners?|artifacts?|spreadsheets?|mock\w{0,3}ups?)\b|\b(?:i can (?:open|try|see rendered|preview|interact with|click around in|c\w{3,5}k around in|actually try|play)|(?:rendered|interactive|live|working|clickable) artifact)\b")
APPEARANCE_PICK = re.compile(r"\b(?:accent|font|typeface|f(?:o[mn]?|no?|in)ts?|(?!acc(?:oun|ep)\w)ac\w{2,4}t)\b")
APPEARANCE_CHECK = re.compile(r"\b(?:misspel\w*|spelling|mangled|botched|options?|list|closest|configured|verify|confirm|look (?:it |the \w+ )?up|look at|available|settings|check|inspect)\b")
JOB_NOUN = re.compile(r"\b(?:jobs?|tasks?|agents?|background work|(?:background|b\w{6,9}d) t\w{1,2}k)\b")
JOB_OWN = re.compile(r"\b(?:i (?:kicked off|dispatched|started|set loose|launched|queued|sent off)|(?:my|the) (?:running |in-flight |background |agent |recent )+(?:jobs?|tasks?|agents?)|background (?:jobs?|tasks?)|in-flight|in my queue|from before|b\w{5,9}d (?:jobs?|tasks?)|in-fl\w{2,4}t|i s\w{1,2}t off|i'?ve queued)\b")
JOB_STATE = re.compile(r"\b(?:status|progress|update|done|complete\w*|finish\w*|wrap(?:ped)? up|still (?:going|running|in progress)|in progress|coming along|movement|news|stand|current state|still g\w{2,4}g|upd\w{2,3}|where do things st\w{1,3})\b")
TOOL_PREFS = re.compile(r"\b(?:disable|enable|turn (?:off|on)|switch (?:off|on)|allow only|only allow)\b[^.]{0,40}\b(?:tools?|search|jobs?|web)\b|\btool preferences\b|\bchat tools\b|\bwhich tools you use\b")
WEB_NAMED = re.compile(r"\b(?:the web|on the web|web search|online|internet|google\w*)\b")
WEB_CUE = re.compile(r"\b(?:news|coverage|articles?|headlines|polls?|reported|reporting|being said|saying about|latest|current(?:ly)?|today'?s?|this week'?s?|these days|what'?s new|changed since|actually changed|happening)\b")
OTHER_SOURCE = re.compile(r"\b(?:tools?|registry|documentation|docs|calendar|workflows?|options|schedules?|jobs?|capabilit\w*|records?|files?|font|accent|appearance|rend\w*|image|picture|repeat|cadence|team|scrape|worker|app|digest|project)\b")
PASS_ALONG = re.compile(r"\b(?:se+n[dt]\w*|e-?mail\w*|mail|forward\w*|pass (?:it|that|this) on)\b")
WEB_NEGATED = re.compile(r"\b(?:don'?t|do not|without|skip|no|never|not)\b[^.?!]{0,30}\b(?:search\w*|online|web|look(?:ing)? ?up|lookup|google\w*|internet)\b(?!\s+(?:s\w{3,6}[ry]|sn\w{2,6}|results?|b\w{2,3}bs?|prev\w{1,4}|excerpts?)\b)")
CALENDAR_ADD = re.compile(r"\bcalendar\b")
# Asked to answer without looking anything up.
FROM_MEMORY = re.compile(r"\b(?:from memory|off the top of your head|from what you know|from general knowledge)\b")
ADD_VERB = re.compile(r"\b(put|pencil|slot|add|book|stick|get|need|want|schedule|block)\b")
# A real date or time in the request (a meeting named "1:1" is not one).
WHEN_GIVEN = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(?:am|pm)\b|\b\d{1,2}(?:st|nd|rd|th)\b|\b\d{1,2}/\d{1,2}\b|\b\d{4}-\d{2}|\b(today|tomorrow|tonight|next week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|afternoon|evening|noon)\b")
WH_QUESTION = re.compile(r"^\W*(?:when|which|what|who|where|how)\b")
DATED = re.compile(r"[\"“”]|\d|\b(today|tomorrow|tonight|next week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|afternoon|evening)\b")
REPEAT = re.compile(r"\b(on a repeat|repeat\w*|every (?:day|week|month|morning|evening|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|each (?:week|month|day)|each w\w{4,5}y|every weekday|first of every|recurring|run every)\b")
REPEAT_VERB = re.compile(r"\b(set up|put|make|schedule|have)\b")
SAVED = re.compile(r"\b(existing|saved|already|the one that)\b")
RUN_SAVED = re.compile(r"\b(?:(?:existing|saved|e\w{3,6}g|s\w{1,3}d) workflow|my w\w{3,6}w that'?s set for|the one already s\w{1,3}d)\b")
RUN_VERB = re.compile(r"\b(start|run|kick|trigger|k\w{2,3} off)\b")
# Passing something on to a person: a sending verb with what is sent or who gets it.
PASS_ALONG_TO = re.compile(r"\bp\w{2,3}s (?:it|the(?: \w+){1,2}) a\w{2,4}g (?:to|on)\b|\b(?:n\w{1,3}d|want) the [\w ]{3,60}? s\w?e?nt to\b")
NOW_CUE = re.compile(r"\b(?:r\w{3,5}t now|as of now)\b")
PASS_ON = re.compile(r"\b(?:send|email|e-mail|mail|forward|shoot|fire off) (?:it|that|this|what|the \w+|them|on)\b|\b(?:get|send) (?:it|that|this) (?:over )?to\b|\bover to\b")
# A request to confirm a stored preference ("confirm / make sure / check my Ditto <setting> is <value>"), read through
# one-edit misspellings of its own few words.
CONFIRM_WORDS = ("check", "confirm", "verify", "color", "colour", "accent", "theme")
CONFIRM_SETTING = re.compile(r"\b(?:confirm|sure|ensure|see to it|check|verify)\b.*\bmy ditto (?:[\w-]+ ){1,2}is\b")

# A request to put a named event on the calendar for a given day: a quoted name, a calendar word (read through close
# misspellings, as in 'clndar') and a weekday or date.
QUOTED_NAME = re.compile(r'["“”]([^"“”]{3,80})["“”]')
EVENT_DAY = re.compile(r"\d|\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")


# A booking named with no calendar word ("Book X for me", "Slot in X for me", "Block out X for me").
FOR_ME = re.compile(r"^\W*([a-z]+)(?:\s+(in|out))?\s+(?!(?:it|this|that|one)\W*for me)[^.?!]{2,60}?\s+for me\W*$")
BOOKING_VERBS = {None: ("book",), "in": ("slot", "pencil"), "out": ("block",)}
# What the calendar holds for a thing: "Do I have X booked / blocked off / scheduled in?", "What's on my calendar about X?"
CALENDAR_HELD = re.compile(r"^\W*do i h\w{1,3}e (?!any\b)[^?.!]{2,60}?\s(?:booked|bl\w{2,3}ed off|scheduled(?: in)?)\W*$")
CALENDAR_ABOUT = re.compile(r"\bwhat'?s on my (\w+) about\b")
# Public talk about a topic, which no record of the user's holds.
PEOPLE_SAYING = re.compile(r"\bwhat (?:are )?(?:people|folks) (?:are )?saying about\b")
# The user's own Ditto settings (accent colour, font, colour mode): a word for one of them, the user's own app or
# setup, and the words that make a message a request to act or a question about options rather than a statement of
# their choice or a question about which value is theirs.
SETTING_MODE = re.compile(r"\b(?:mode|theme)\b")
SETTING_ANY = re.compile(r"\b(?:colou?r|appearance)\b")
OWN_SETUP = re.compile(r"\bmy\b")
OWN_APP = re.compile(r"\b(?:ditto|app|interface|workspace|appearance|typeface)\b")
SETTING_REQUEST = re.compile(r"\b(?:can you|could you|would you mind|please (?:set|change|switch|make|use|apply|turn)|how (?:do|does|can|could|would|should|to)|where (?:do|does|can|is|are)|a way|see to it|that my|device|options?|available|list\w*|check\w*|confirm\w*|sure|ensure|verify|inspect\w*|look (?:up|at|it up|into)|tools?|capabilit\w*|features?|support\w*|feedback|team|devs|report\w*|send|email|file|save|remember|store|note (?:it|that|this) down)\b")
STATED_REQUEST = re.compile(r"(?<!n't )(?<!not )\b(?:set|sets|switch\w*|change\w*|make|use|using|apply\w*|turn|match\w*|adjust\w*|update\w*|recolou?r\w*|pick|choose|try|add|find|give|tell|show)\b")
OWN_SETTING_STATED = ("This message tells you the user's own standing choice for one of their Ditto settings and asks for "
                      "nothing to be done: change no setting and call no tool. Reply with one short sentence of your own "
                      "saying you have noted it, naming the value they gave in double quotation marks, spelled exactly as "
                      "they wrote it, and nothing more.")
OWN_SETTING_ASKED = ("This asks which value {which} should have. Answer with the value the user's own saved "
                     "preference for that setting gives, even where their note does not use the setting's name: a font "
                     "is given by a typeface name, an accent by a colour name, and a colour mode is dark, light or system. "
                     "Give that one value in double quotation marks, spelled as the note writes it. A value for another of "
                     "their settings, or one they tie to a client, a project or anyone else, is not it. Change no setting, "
                     "and do not ask them which value they want.")

# The user's own notes about how their Ditto looks, among the records shown with a question about their own Ditto font:
# short records whose user side names Ditto and a look word and is not about reasoning effort (read through the central
# fold, so one-letter slips still count).
OWN_LOOK_APP = re.compile(r"\bditto\b")
OWN_LOOK_WORD = re.compile(r"\b(?:look|looks|appearance|accent|colou?rs?|mode|theme|font|typeface|interface|workspace|style)\b")
OWN_LOOK_OTHER = re.compile(r"\b(?:reasoning|effort)\b")
OWN_LOOK_MAX_CHARS = 400
OWN_LOOK_MARKS = ("Of the records above, {marks} {verb} the user's own {notes} about how their Ditto looks; each gives one of "
                  "its three appearance settings (an accent colour, a font or a colour mode), whatever words it uses, so the "
                  "one of them that gives neither a colour nor dark, light or system gives the font.")

OWN_LOOK_ADDED = 6


def is_own_look_note(text: str) -> bool:
    """A short record whose user side names Ditto and a look word and is not about reasoning effort."""
    if len(text) > OWN_LOOK_MAX_CHARS or not any(one_edit(word, "ditto") for word in re.findall(r"\b[a-z]{4,6}\b", text.lower())):
        return False
    seen = folded(text)
    return bool(OWN_LOOK_APP.search(seen) and OWN_LOOK_WORD.search(seen) and not OWN_LOOK_OTHER.search(seen))


def own_look_marks(request: str, records: list[tuple[str, str]]) -> str:
    """For a question about the user's own Ditto font, the sentence naming the shown records (given as (mark, user side))
    that are the user's own notes about how their Ditto looks; otherwise an empty string."""
    if own_setting(request) != "asked" or own_setting_named(request) != "font":
        return ""
    marks = []
    for mark, text in records:
        if len(text) > OWN_LOOK_MAX_CHARS:
            continue
        seen = folded(text)
        if OWN_LOOK_APP.search(seen) and OWN_LOOK_WORD.search(seen) and not OWN_LOOK_OTHER.search(seen):
            marks.append(mark)
    if not marks:
        return ""
    listed = marks[0] if len(marks) == 1 else ", ".join(marks[:-1]) + " and " + marks[-1]
    return OWN_LOOK_MARKS.format(marks=listed, verb="is" if len(marks) == 1 else "are", notes="note" if len(marks) == 1 else "notes")


def own_setting(request: str) -> str:
    """'stated' when the message states the user's own choice for one of their Ditto settings and asks for nothing,
    'asked' when it asks which value one of their own settings should have, else an empty string."""
    text = folded(request)
    if not (APPEARANCE_PICK.search(text) or SETTING_MODE.search(text) or SETTING_ANY.search(text)):
        return ""
    if not OWN_SETUP.search(text) or not OWN_APP.search(text) or SETTING_REQUEST.search(text) or PLANNING.search(text):
        return ""
    if ASKS.search(text):
        return "asked" if own_setting_named(request) else ""
    return "" if STATED_REQUEST.search(text) else "stated"


def own_setting_named(request: str) -> str:
    """The setting a question about the user's own Ditto settings names, when its words say which."""
    text = folded(request)
    pick = APPEARANCE_PICK.search(text)
    if pick:
        return "font" if pick.group(0)[0] in "ft" else "accent colour"
    return "colour mode" if SETTING_MODE.search(text) else ""


def own_setting_asked_hint(request: str) -> str:
    name = own_setting_named(request)
    which = f"the user's own Ditto {name}" if name else "one of the user's own Ditto settings (accent colour, font or colour mode)"
    return OWN_SETTING_ASKED.format(which=which)


def books_for_me(text: str) -> bool:
    match = FOR_ME.match(text)
    return bool(match) and any(one_edit(match.group(1), verb) for verb in BOOKING_VERBS[match.group(2)])


def finds_on_calendar(text: str) -> bool:
    about = CALENDAR_ABOUT.search(text)
    return bool(CALENDAR_HELD.match(text)) or bool(about and (names_calendar(about.group(1)) or re.fullmatch(r"c\w{5,8}r", about.group(1))))


def names_calendar(text: str) -> bool:
    """A word that is "calendar" or a close misspelling of it (difflib similarity of at least 0.75)."""
    return any(word == "calendar" or (len(word) >= 6 and SequenceMatcher(None, word, "calendar").ratio() >= 0.75) for word in WORD.findall(text.lower()))

HINTS = {
    "agreed": "This refers to a decision on record: the user's records hold what was settled for the thing named (often under that nickname in quotes). Do exactly what that record says, with the exact name it gives and through the tool it names, even though the request calls the task something else.",
    "research-send": "This asks for a current value to be looked up and passed on: search the web for the thing named first, with the web search tool (the figure is not in the user's records), then send the figure the result gives for that exact thing, with its unit and no other figures, in the body, to the current address the user's records give for the person the message names by name or nickname (their records, when repeated just before the message, are the ones to use); a 'them' later in the message, even misspelt, is that same person.",
    "confirm-setting": "This asks to confirm a stored preference. If the user's records already give that same value for that setting, reply "
                       "that it is already set to it, citing the record, and call no tool at all, not even to look the setting up; a note may "
                       "name the setting in other words (the chat font as their interface font or typeface, the accent as the app's colour, "
                       "the colour mode as its look) and it is still the same setting. Otherwise, when the value differs even by one word "
                       "(navy is not dark navy), set it now to the value the user names.",
    "planning-send": "'Them' is whoever the user's note for this names. If that note says the user has not decided who gets it (several people asked and none was chosen), ask which of them it goes to, naming each, and send nothing; otherwise send it now to that person's address.",
    "send": "'Them' is the person the user's records name for this; send it now to that person's current address, with a body that refers to the thing by its name, rather than asking for its content.",
    "effort": "If the user's note says they have not settled on a default, ask which reasoning effort level they want, quoting both styles the note names in its own words; otherwise set the level their note gives.",
    "handoff": "The note to change is the handoff note itself, the record kept for the handoff or scheduling details of the thing named (often called its handoff scratchpad), not its planning notes or its identity, ownership or history record. Change that note in place with the corrected fact in a few words, keeping the name of the thing it is about so the note can still be found: the name in quotes, a colon, then each changed thing named plainly, 'is', and its new value, the handoff day always as 'handoff is' and the day whatever the request calls it, for example '\"seagate side plan\": handoff is Monday', with another fact such as 'reviewer is' and the name when that changed too, spelled correctly, leaving out the note's old text.",
    "run-saved": "List the saved workflows, find the one the user describes, and start it by passing its name exactly as listed in `name`.",
    "repeat": "This sets up something new that repeats: create the workflow with its schedule now, with steps that follow from what the user wants done, without listing the existing workflows beforehand or asking for details they did not give.",
    "calendar-named": "Read the user's note on this event first. If it says the event is already on the calendar, it is: search the calendar for it and report where it sits, creating nothing, even if the search shows nothing. If it says the event is not on the calendar yet, create it now for the day the user gives, without asking which week or what time. With no such note, search first: an event with that name found on any day is already there; create it only if the search finds none.",
    "calendar-find": "This asks what the calendar holds for the thing named: search the calendar once, naming it, and answer from what the search returns.",
    "calendar-add": "Add it to the calendar now. No day or time is given, so add it without one (time not specified) rather than asking, and without searching the calendar first.",
    "workflow": "Start by listing the saved workflows. If none of them is for this, create one under the formal name the records give the project (not its nickname), with the requested step written into steps, such as the reviewer's current email address from the records.",
    "how-to": "This asks how to do something in Ditto: look it up with the capabilities tool and explain what it returns, without changing any setting.",
    "earlier-image": "This points at an image from earlier: edit it with the image-editing tool, passing your words for that image as its image_url, rather than asking for a link.",
    "sandbox": "Run it in the code sandbox now, as the only call: a short program that runs or prints the routine the user names, "
               "calling it by that name (the sandbox already holds it), rather than searching the web for it, starting a background job "
               "or asking for its source.",
    "capabilities": "This asks what Ditto can do or where a setting is: look it up with the capabilities tool now and answer from what it returns, without changing any setting.",
    "workflow-new": "This asks for a new saved workflow: create it now with the workflow-creating tool, with the steps the user describes or, when they name none, steps that follow from its name or purpose, rather than asking for steps, starting a background job or listing the saved workflows first.",
    "agent-job": "This asks for the work to be done, not explained: start it now as a background agent job with the user's objective as its task, rather than writing the code or the steps in the reply.",
    "schedules": "This asks what runs on its own on a schedule (recurring, timed or repeating): that is what the schedule-listing tool returns, each run time and how many runs it has logged; the saved-workflow list does not show schedules. Call it and answer from its result.",
    "tool-lookup": "This asks which of your tools fits a job: look through them with one call to the tool-search tool and answer from what it returns, without searching them again.",
    "arithmetic": "This asks for arithmetic over figures the message states: compute it with the code-running tool in one short snippet that prints every figure asked for, as the only call, and report the result, even when the user says no script or project is needed; that only rules out building something bigger.",
    "feedback": "This is feedback meant for the Ditto team: file it with the team-feedback tool, its text in the user's words. It is not an email to anyone.",
    "colour-mode": "This asks to set the app's colour mode now: set it to dark or light as asked, or to follow the device when that is asked, even if a note mentions another mode; the request is the current instruction.",
    "search-read": "Search the web for it, then open the top result's link with the page-reading tool and answer from that page.",
    "web-read": "Search the web for it, then open the top result's link with the page-reading tool and answer from that page.",
    "effort-set": "This is about how much reasoning goes into replies from now on: set it now with the reasoning-effort tool to the level the message states (deep, hard, careful or thorough thinking, taking time or maxing it out: high; balanced, moderate or middle-of-the-road: medium; quick, light, minimal, snappy or fast, not overthinking: low).",
    "calendar-pending": "This refers to an event in the user's notes for this planning context. When that note gives the event's day or time (for example 'Monday at 8am'), create it now with the calendar-creating tool, titled with the event's name as the note words it and dated as the note says, without asking. Only when the note says the event has no date yet, add nothing and ask when, naming the event exactly as the note words it (for example 'the dentist check-up').",
    "delete-one": "This asks to delete one stored note and keep the person's other records: find that note itself (search the stored memories for its words when it is not shown above) and delete it with the pairID the records show for it, copied whole. Never use the pairID of their contact, work or email record, and never an id that no record shows.",
    "artifact": "This asks for something the user can open and use: build it now with the artifacts tool, filling in details with sensible placeholders rather than asking for them, and not as an image or as text in the reply.",
    "appearance-pick": "This sets an appearance option from the workspace's own list: look the options up with the capability-discovery tool, then call the setting tool with the one listed option the user means, spelled exactly as listed; a reply that says it is set without that call leaves it unset. Their name for it may be misspelt: read it as the listed name it is a letter or two off (letters changed, added or dropped), not one close in meaning or look ('grafite' is graphite, not slate). When they ask for the X shade, variant, version, cut or edition of a name, first read that name as the listed word it is a letter or two off, then take the listed option that holds both that word and X (the bold version of Robto: the word is Roboto, the option the listed one with Roboto and Bold), never an option picked by its colour or meaning and never the plain name alone.",
    "job-status": "This asks how background jobs the user already started are doing: list them with the job-listing tool and answer from what it returns. Start nothing new, and do not use the saved-workflow list, which does not show jobs.",
    "save": "This asks you to remember something the user tells you: store it now with the memory-saving tool, in one call that holds the fact in the user's words, without searching the stored memories first, then acknowledge it briefly.",
    "tool-prefs": "This changes which tools are on in chats: make the change now with the chat tool-preferences tool; a reply that says it is done without that call leaves it undone.",
    "no-web": "The user asks for an answer without searching the web: make no web search or other outside call, and answer in a full sentence of your own, not a bare word, from the user's records when they hold it, otherwise from what you know.",
    "web": "If you search the web for this, one search is enough: one query naming the thing asked about, then work from what it returns, even when it looks thin, rather than searching again, and say what it does not cover. Search again only if the search itself fails with an error.",
}


def confirm_folded(text: str) -> str:
    """The text, lower-cased, with each word of five or more letters one edit off exactly one of CONFIRM_WORDS read as it."""
    def snap(match: re.Match) -> str:
        word = match.group(0).lower()
        if len(word) < 5 or word in CONFIRM_WORDS:
            return word
        near = [key for key in CONFIRM_WORDS if one_edit(word, key)]
        return near.pop() if len(near) == 1 else word
    return WORD.sub(snap, text)


DELETE_CUES = ("clear", "clean", "drop", "delete", "remove", "toss", "stale", "clutter")
NOTE_CUES = ("note", "notes", "receipt", "entry", "scratch", "throwaway", "stuff")
KEEP_CUES = ("keep", "stays", "stay", "touched", "else", "just", "only", "leave", "actual", "nothing")


def has_cue(words: list[str], cues: tuple[str, ...]) -> bool:
    return any(word == cue or (len(word) >= 4 and len(cue) >= 4 and one_edit(word, cue)) for word in words for cue in cues)


def deletes_one(text: str) -> bool:
    """A clearing word, a note word and a keep-the-rest word, each read through one-edit slips."""
    words = WORD.findall(text)
    return (has_cue(words, DELETE_CUES) or re.search(r"\bcan go\b", text) is not None) and has_cue(words, NOTE_CUES) and has_cue(words, KEEP_CUES)


EFFORT_FOLD = ("think", "thinking", "reasoning", "reason", "effort", "depth", "hard", "deeply", "balanced", "carefully",
               "thoroughly", "usual", "normally", "moderate")
NOT_EFFORT = frozenset("thing things thank thanks thin thick season seasons treason card hand harm yard herd held hare".split())


def effort_folded(text: str) -> str:
    """The text with each word one edit off exactly one effort word read as it."""
    def snap(match: re.Match) -> str:
        word = match.group(0)
        if len(word) < 4 or word in EFFORT_FOLD or word in NOT_EFFORT:
            return word
        near = [cue for cue in EFFORT_FOLD if one_edit(word, cue)]
        return near.pop() if len(near) == 1 else word
    return WORD.sub(snap, text)


def looks_up(text: str) -> bool:
    """"look up" with "look" misspelled within one edit."""
    words = WORD.findall(text)
    return any(one_edit(first, "look") and second == "up" for first, second in zip(words, words[1:]))


SEARCH_CUES = ("search", "research", "google", "googled")
READ_CUES = ("open", "read", "summarize", "summarise", "recap", "follow")
PAGE_CUES = ("result", "source", "page", "link", "hit")
ORDINAL_CUES = ("top", "first", "best", "leading")


def searches_then_reads(text: str) -> bool:
    """A search word (or "look up"), a read word and a page word or an ordinal, each read through one-edit slips, in a
    message that names no other source (tools, settings, records and the like)."""
    if OTHER_SOURCE.search(text):
        return False
    words = WORD.findall(text)
    searched = has_cue(words, SEARCH_CUES) or looks_up(text) or re.search(r"\blook\w*\s+up\b", text) is not None
    reading = [word for word, after in zip(words, words[1:] + [""]) if after.lower() not in ("out", "up")]
    read = has_cue(reading, READ_CUES) or re.search(r"\bboil (?:it )?down\b|\bgist\b", text) is not None
    return searched and read and (has_cue(words, PAGE_CUES) or has_cue(words, ORDINAL_CUES))


def reads_page(text: str) -> bool:
    """A request to open or read a page, source, link or result (a read word and a page word), or one that names the
    top, first, best or leading source or page (not a search result), each read through the existing cue lists."""
    words = WORD.findall(text)
    reading = [word for word, after in zip(words, words[1:] + [""]) if after.lower() not in ("out", "up")]
    ranked = any(first.lower() in ORDINAL_CUES and has_cue([second], ("source", "page")) for first, second in zip(words, words[1:]))
    return (has_cue(reading, READ_CUES) and has_cue(words, PAGE_CUES)) or ranked


def product_tool(request: str, tool_names: list[str]) -> str:
    """The listed tool whose leading name part (a product name, not a generic word) the request names."""
    words = {re.sub(r"'s?$", "", word.lower()) for word in WORD.findall(request) if len(word) >= 4}
    found = []
    for name in tool_names:
        part = name.lower().split("_")[0]
        if len(part) < 4 or part in GENERIC_PARTS:
            continue
        if part in words or (len(part) >= 5 and any(one_edit(part, word) for word in words)):
            found.append(name)
    return found.pop() if len(found) == 1 else ""


def slips_read(text: str) -> str:
    """The text with each slip read as the pattern word it stands for and every other word as written (case kept)."""
    folds = iter(WORD.findall(folded(text)))
    return WORD.sub(lambda match: (lambda word: match.group(0) if word == match.group(0).lower() else word)(next(folds)), text)


def request_kind(request: str, tool_names: list[str] | None = None) -> str:
    text = folded(request)
    # The question test reads past a polite lead-in ("When you're ready, ..."), which is not itself a question.
    asked = folded(after_polite_lead(request))
    if tool_names and product_tool(request, tool_names):
        return "product"
    if AGREED.search(text):
        return "agreed"
    effort_text = effort_folded(text)
    if (EFFORT.search(effort_text) or EFFORT_ANY.search(effort_text)) and (EFFORT_USUAL.search(effort_text) or PLANNING.search(text)):
        return "effort"
    if EFFORT_ANY.search(effort_text) and EFFORT_LEVEL.search(effort_stated(effort_text)) and not ASKS.search(EFFORT_LEAD.sub("", text)):
        return "effort-set"
    if EFFORT_SETTING.search(effort_text) and not ASKS.search(EFFORT_LEAD.sub("", text)):
        return "effort"
    if CONFIRM_SETTING.search(confirm_folded(request)):
        return "confirm-setting"
    if SENDING.search(text) and PLANNING.search(text):
        return "planning-send"
    if (passes_on(request) or passes_on(slips_read(request)) or PASS_ALONG_TO.search(text)) and (LOOKUP.search(text) or looks_up(text) or WEB_CUE.search(text) or NOW_CUE.search(text) or re.search(r"\bw\w{2,4}e\b[^.?!]{0,60}\bstands?\b", text)) and not re.search(r"\bworkflows?\b|\bif not\b", text) and not TEAM_FEEDBACK.search(text):
        return "research-send"
    if PASS_ON.search(text) and (LOOKUP.search(text) or looks_up(text)) and not re.search(r"\bworkflows?\b|\bif not\b", text) and not ASKS.search(asked) and not TEAM_FEEDBACK.search(text):
        return "research-send"
    if SENDING.search(text) and re.search(r"\b(them|tehm|thme|thm|thzm|ttem|thdm|tem|(?:th\w{1,2}m|t\w?em))\b", text) and (not LOOKUP.search(text) or re.search(r"\b(?:figures|numbers|f\w{4,5}s) are r\w{3,4}y\b", text)):
        return "send"
    if HANDOFF.search(text) and WEEKDAY.search(text) and not ASKS.search(asked):
        return "handoff"
    if WORKFLOW_CHECK.search(text) and WORKFLOW_CREATE.search(text):
        return "workflow"
    if RUN_SAVED.search(text) and RUN_VERB.search(text) and not NEW_SAVED.search(text):
        return "run-saved"
    if REPEAT.search(text) and REPEAT_VERB.search(text) and not SAVED.search(text) and not (SCHEDULE_TOPIC.search(text) and SCHEDULE_ASK.search(text) and ASKS.search(asked)) and not HOW_TO.search(text):
        return "repeat"
    if (names_calendar(request) or re.search(r"\bschedule\b", text)) and PLANNING.search(text) and PENDING_REF.search(text) and not QUOTED_NAME.search(request) and not WH_QUESTION.search(text):
        return "calendar-pending"
    if names_calendar(request) and QUOTED_NAME.search(request) and EVENT_DAY.search(text) and not PLANNING.search(text) and not ASKS.search(asked):
        return "calendar-named"
    if (names_calendar(request) or re.search(r"\bpencil\s+\w+(?:\s+\w+)?\s+in\b|\bpencil in\b", text)) and ADD_VERB.search(text) and not QUOTED_NAME.search(request) and not WHEN_GIVEN.search(text) and not PLANNING.search(text) and not WH_QUESTION.search(text):
        return "calendar-add"
    if books_for_me(text) and not WHEN_GIVEN.search(text) and not PLANNING.search(text):
        return "calendar-add"
    if finds_on_calendar(text) and not PLANNING.search(text):
        return "calendar-find"
    if (APPEARANCE_PICK.search(text) or (re.search(r"[a-z]-ish\b", text) and re.search(r"\ba[a-z]{5,9}ce\b", text))) and APPEARANCE_CHECK.search(text) and not re.search(r"\bmode\b", text) and not ASKS.search(asked):
        return "appearance-pick"
    if HOW_TO.search(text) and not CONTACT_ASK.search(text):
        return "how-to"
    if EARLIER_IMAGE.search(text) and not (JOB_NOUN.search(text) and JOB_OWN.search(text) and JOB_STATE.search(text)):
        return "earlier-image"
    if SANDBOX.search(text):
        return "sandbox"
    if CAPABILITY_ASK.search(text) and not CONTACT_ASK.search(text):
        return "capabilities"
    if WORKFLOW_NEW.search(text) and (MAKE_VERB.search(text) or NEW_SAVED.search(text)) and not (SAVED.search(text) and not NEW_SAVED.search(text)) and not WORKFLOW_CHECK.search(text):
        return "workflow-new"
    if JOB_NOUN.search(text) and JOB_OWN.search(text) and JOB_STATE.search(text):
        return "job-status"
    if JOB_GO.search(text) and JOB_WORK.search(text) and not JOB_NOT.search(text) and not ASKS.search(asked):
        return "agent-job"
    if ARTIFACT_ASK.search(text) and (not ASKS.search(asked) or re.search(r"^\W*can you (?:build|make|create|put together|design|whip up|m\w{2,3}k up)\b", text)) and not JOB_WORDS.search(text):
        return "artifact"
    if (deletes_one(text) or (DELETE_ONE.search(text) and ONE_NOTE.search(text) and KEEP_REST.search(text))) and not ASKS.search(asked):
        return "delete-one"
    if SCHEDULE_TOPIC.search(text) and SCHEDULE_ASK.search(text) and (not REPEAT_VERB.search(text) or ASKS.search(asked)):
        return "schedules"
    if TOOL_LOOKUP.search(text):
        return "tool-lookup"
    if STATED_ARITHMETIC.search(text) and re.search(r"\d", text):
        return "arithmetic"
    if TEAM_FEEDBACK.search(text):
        return "feedback"
    if COLOUR_MODE_SET.search(text):
        return "colour-mode"
    if SAVE_CUE.search(text) and not ASKS.search(asked):
        return "save"
    if TOOL_PREFS.search(text):
        return "tool-prefs"
    if (SEARCH_THEN_READ.search(text) or searches_then_reads(text)) and not WEB_NEGATED.search(text):
        return "search-read"
    setting = own_setting(request)
    if setting:
        return "own-setting-" + setting
    if (WEB_NAMED.search(text) or (WEB_CUE.search(text) and not OTHER_SOURCE.search(text))) and not WEB_NEGATED.search(text) and not PASS_ALONG.search(text):
        return "web-read" if reads_page(text) else "web"
    if (WEB_NEGATED.search(text) or FROM_MEMORY.search(text)) and ASKS.search(asked) and not re.search(r"\b(?:open|page|pages|link|links|read)\b", text):
        return "no-web"
    return ""


# Kinds whose line is only about calling a named tool: a request with one of them belongs to the action lane.
TOOL_KINDS = frozenset((
    "tool-lookup capabilities schedules job-status workflow workflow-new run-saved repeat effort effort-set calendar-named "
    "calendar-add calendar-find calendar-pending artifact agent-job arithmetic delete-one colour-mode tool-prefs feedback search-read "
    "sandbox handoff agreed"
).split())


def tool_kind(request: str, tool_names: list[str] | None = None) -> bool:
    kind = request_kind(request, tool_names)
    return kind in TOOL_KINDS or (kind in ("web", "web-read") and PEOPLE_SAYING.search(folded(request)) is not None)


def tool_hint(request: str, tool_names: list[str] | None = None) -> str:
    hint = request_hint(request, tool_names)
    return f"{HOST_NOTE} {hint}" if hint else ""


def request_hint(request: str, tool_names: list[str] | None = None) -> str:
    kind = request_kind(request, tool_names)
    if kind == "product":
        tool = product_tool(request, tool_names or [])
        opens = (" Its result may give that figure under a label of its own (a confirmation, status line, summary or "
                 "latest update) rather than as the id, code or number the message asks for: that figure is the one to "
                 "report, so report it rather than saying no id or number was given.")
        return (f"The message names the {tool} tool: call {tool} now with the thing the message names as its input; its result "
                "carries the figure, so do not ask for the input or search for it beforehand. The value asked for is the figure the result gives for the thing the message names, whatever the result calls it (a number, code, id or reading): give it exactly, alone, and leave out figures the result gives for other things." + opens)
    if kind == "own-setting-asked":
        return own_setting_asked_hint(request)
    if kind == "own-setting-stated":
        return OWN_SETTING_STATED
    return HINTS.get(kind, "")
