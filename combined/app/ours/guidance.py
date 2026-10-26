"""Advisory notes for the action lane, chosen from the request's wording and the tools it offers.

Each note describes how a careful assistant handles one kind of request with the tools at hand. A
note appears only when the request reads as that kind and the catalog offers the tool it names; the
deciding model still sees the whole request, the records and the whole catalog, and makes every call
and writes every answer itself. Nothing here removes, forces or rewrites anything.

"""
from __future__ import annotations

import re
from collections.abc import Iterable

WORD = re.compile(r"[A-Za-z][A-Za-z']*")


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


# What the request is about.
APPEARANCE = _rx(r"\b(?:accent|font|typeface|theme|colou?r m\w{2,3}|dark mode|light mode|appearance|light or dark|dark or light)\b")
OWN_SETTING = _rx(r"\bmy\b[^.?!]{0,30}\b(?:accent|font|typeface|theme|colou?r m\w{2,3}|mode|appearance)\b[^.?!]{0,30}\b(?:is|stays|set to)\b")
CORRECTION = _rx(r"\b(?:moved|shifted|changed|is now|now on|instead of)\b|\b(?:fix|correct|update|amend)\b[^.?!]{0,30}\b(?:note|what's there|entry|record)\b")
NOTE_WORDS = _rx(r"\bnotes?\b|\bscratchpad\b|\brecord\b|\bentry\b")
DELETE = _rx(r"\b(?:delete|remove|clear|drop|bin|get rid of|toss|discard)\b")
DISPOSABLE = _rx(r"\b(?:receipt|scratch|throwaway|temporary|disposable|leftover|no longer needed)\b")
IMAGE = _rx(r"\b(?:picture|image|photo|render|drawing|illustration)\b")
EARLIER = _rx(r"\b(?:you (?:just )?(?:made|drew|created|generated)|from (?:before|earlier)|(?:last|latest|previous|earlier) one|that (?:picture|image|photo)|the (?:last|latest|previous) (?:picture|image|photo|render))\b")
CHANGE = _rx(r"\b(?:change|edit|update|touch up|tweak|adjust|make|swap|replace|brighten|recolou?r|crop)\b")
SEND = _rx(r"\b(?:send|email|mail|forward|pass|get|shoot|fire off|deliver|share)\b")
TO_THEM = _rx(r"\b(?:over to them|back to them|along to them|out to them|them (?:my|the|our) (?:[\w'-]+ ){0,5}?(?:update|numbers|figures|summary|report|news))\b")
CALENDAR_PUT = _rx(r"\b(?:on|onto|to|into|in)\s+(?:my|the)\s+(?:calendar|schedule)\b")
UNNAMED = _rx(r"\b(?:that|it|this|them)\s+(?:on|onto|to|into|in)\s+(?:my|the)\s+(?:calendar|schedule)\b")
SCHEDULED = _rx(r"\b(?:schedul\w*|recurring|repeating|on a timer|timed|automatic\w*|on their own|hands[- ]off|cadence|runs? (?:daily|weekly|twice|every))\b")
RUNS = _rx(r"\bworkflows?\b|\bruns?\b|\bjobs?\b|\bautomations?\b")
WORKFLOW = _rx(r"\bworkflows?\b")
RUN_VERB = _rx(r"\b(?:run|start|kick off|launch|trigger|fire)\b")
SAVED = _rx(r"\b(?:saved|existing|my|already)\b")
DO_NOW = _rx(r"\b(?:start working|get (?:going|started)|carry (?:it )?out|do (?:it|this) now|right away|kick it off|actually do)\b")
EFFORT = _rx(r"\b(?:reasoning|how (?:hard|deeply|much) you think|think (?:hard|harder|deeply|it through|things through)|thinking (?:level|depth|effort))\b")
TOOL_ASK = _rx(r"\b(?:which (?:of your )?tools?|what tool|tool binding|right tool|tool for)\b")
LIVE = _rx(r"\b(?:latest|right now|currently|current|today|these days|at the moment|as of now)\b")
FIGURE = _rx(r"\b(?:figure|number|reading|value|level|price|rate|index|count|score)\b|\bat\b[^.?!]{0,20}\bnow\b")
RECIPIENT = _rx(r"\b(?:to|over to|along to|with)\s+[A-Z][a-z]+\b")
DEVICE = _rx(r"\b(?:device|system setting|system|operating system|phone|laptop)\b")
KEEP = _rx(r"\b(?:remember that|note (?:for later|it down|that)|keep in mind|for the record|hold on(?:to)? that|store this|save this)\b")
SANDBOX = _rx(r"\b(?:code sandbox|sandbox|run the routine|execute the routine)\b")
READ_PAGE = _rx(r"\b(?:open|read)\b[^.?!]{0,30}\b(?:page|source|link|article|site)\b|\bread it\b|\bnot the (?:search )?(?:snippet|preview|summary|blurb)\b")
LOOSE_NAME = _rx(r"\b(?:loosely|approximate|closest|matching option|spelling|spelt|spelled)\b")

GENERIC_HEADS = frozenset({"search", "list", "set", "run", "create", "edit", "read", "file", "save", "update", "delete", "fetch",
                           "calendar", "gmail", "execute", "discover", "apply", "artifacts", "get", "send", "add", "remove"})


def tool_names(tools: Iterable) -> list[str]:
    return [getattr(tool, "name", tool) for tool in tools]


def add_on_tools(request: str, names: list[str]) -> list[str]:
    """Catalog tools the request names by the leading word of their name, other than the everyday product tools."""
    words = {word.lower() for word in WORD.findall(request)}
    named = []
    for name in names:
        head, joined, _ = name.partition("_")
        if joined and len(head) >= 3 and head not in GENERIC_HEADS and head in words:
            named.append(name)
    return named


def guidance(request: str, tools: Iterable) -> list[str]:
    names = tool_names(tools)
    offered = set(names)
    text = request
    notes: list[str] = []
    # with or without "make sure" / "check": a stated value for the user's own setting is checked against their note
    setting = bool(APPEARANCE.search(text) and OWN_SETTING.search(text)) and bool(offered & {"set_accent_color", "set_chat_font", "set_theme"})
    if setting:
        notes.append("Checking a setting: the message asks you to make sure one of the user's own settings (accent colour, chat font or colour mode) has a value. Read the user's note that keeps their value for that setting first. If it already keeps the value the message names, nothing needs changing: make no call at all, not even a lookup, and say it is already set, quoting the value as the note writes it. If the note keeps another value, call that setting's setter with the value the message names.")
    correcting = "update_memory" in offered and bool(CORRECTION.search(text) and NOTE_WORDS.search(text)) and not DELETE.search(text)
    if correcting:
        notes.append("Correcting a saved note: change the note the message means with update_memory on its pair id. The new content states each corrected fact as the name of the thing, in the message's own word for it, followed by its new value (as in 'deadline is Thursday', never just 'moved to Thursday'), and every other fact the message changes the same way; do not add a second note or touch other records.")
    if "delete_memory" in offered and DELETE.search(text) and DISPOSABLE.search(text):
        notes.append("Deleting one note: remove only the note the message points at, with delete_memory on that note's own pair id. The person's other records (their contact, workplace or email notes) stay, even when the note mentions them.")
    if "edit_image" in offered and IMAGE.search(text) and EARLIER.search(text) and CHANGE.search(text):
        notes.append("Changing an earlier image: the message means an image made earlier in this conversation. Call edit_image right away, with image_url naming that image as the user refers to it and the change as the instruction; do not ask for a link and do not make a new image.")
    if "gmail_send" in offered and SEND.search(text) and TO_THEM.search(text):
        notes.append("Sending to 'them': the message leaves the recipient as 'them'. The user's note on this project says who it goes to: whoever requested it, if anyone did, otherwise the recipient the note plans for. Send it right away with gmail_send to that person's email address exactly as their record gives it (a name alone is not an address); the body says the update or figures are ready. If the note says nobody has been chosen yet, send nothing and ask who should get it, naming the people the note mentions.")
    elif {"search_web", "gmail_send"} <= offered and LIVE.search(text) and FIGURE.search(text) and SEND.search(text) and RECIPIENT.search(request):
        notes.append("Looking up a figure and sending it: look the figure up with search_web first, then send it with gmail_send to the person's current email address as their records give it (a later correction replaces an older address). Put the figure in the email exactly as the result writes it, and repeat it in your reply.")
    # only when the message names the event; "put that on my calendar" is left to the lane prompt
    if "calendar_create_event" in offered and CALENDAR_PUT.search(text) and not UNNAMED.search(text):
        notes.append("Adding to the calendar: read the user's notes about this event first. If a note says the event is booked already, find it with calendar_search_events by its name and say where it is; do not add it again. Only if a note says its date is still undecided, add nothing and ask when, naming the event as the note does. In every other case create it right away with calendar_create_event, titled with the event's name: a day the message gives is used as given (the coming one), and a missing time is left open, so do not ask which week or what time.")
    if "list_schedules" in offered and SCHEDULED.search(text) and RUNS.search(text) and not (RUN_VERB.search(text) and WORKFLOW.search(text) and not re.search(r"\?", request)):
        notes.append("Workflows that run on their own: which saved workflows run on a schedule, when they run and how many runs they have logged is what list_schedules returns (list_workflows lists the workflows themselves, not their schedules). Call list_schedules and answer from it.")
    if {"list_workflows", "run_workflow"} <= offered and RUN_VERB.search(text) and WORKFLOW.search(text) and SAVED.search(text):
        notes.append("Running a saved workflow: call list_workflows, pick the workflow whose name or schedule matches the message, then call run_workflow with its name exactly as listed (not its id).")
    if "execute_agent_job" in offered and DO_NOW.search(text):
        notes.append("Doing a task now: the message asks for a piece of work to be carried out now, not explained. Start it with execute_agent_job, the task in the user's words; do not look up jobs or workflows first.")
    if "set_reasoning_effort" in offered and EFFORT.search(text):
        notes.append("Reasoning depth: how deeply you should think is set with set_reasoning_effort: deep or thorough is high, balanced or moderate is medium, quick or minimal is low. If the message asks for the user's usual level, use the level their note names; if the note says they have not settled on one, ask which they want, naming the options the note mentions.")
    if "search_tools" in offered and TOOL_ASK.search(text):
        notes.append("Finding a tool: the message asks which of your tools fits a job. Look with search_tools first and answer from what it finds; do not run anything else.")
    if "set_theme" in offered and APPEARANCE.search(text) and DEVICE.search(text) and not setting:
        notes.append("Colour mode: following or matching the user's device or system is the theme value 'system'. Set it directly with set_theme; no lookup is needed first.")
    if "save_memory" in offered and KEEP.search(text) and not correcting:
        notes.append("Saving a note: save what the user said with save_memory directly; there is no need to search the notes first. Then confirm what you saved, quoting it as the user wrote it.")
    if "run_code" in offered and SANDBOX.search(text):
        notes.append("Running code: run it once with run_code, a short snippet that calls the routine by the name the user gives, and report exactly what it prints; no web search or background job is needed.")
    if {"search_web", "read_links"} <= offered and READ_PAGE.search(text):
        notes.append("Reading a page: search once with search_web, then open the top result's link exactly as it was returned with read_links, and answer from the page itself, since search previews can carry different figures. One search and one read are enough.")
    if "discover_capabilities" in offered and any(name.startswith("set_") for name in offered) and LOOSE_NAME.search(text):
        notes.append("Choosing a listed option: when the message names a setting's value loosely or misspelled (a font, a colour, a mode), list the options with discover_capabilities and choose the listed option closest to the message's spelling letter by letter, not one that only shares a word or a meaning; when it names a cut or variant of a name, choose the listed option that carries that variant.")
    add_ons = add_on_tools(request, names)
    if add_ons:
        notes.append("Named add-on tool: the message names the listed tool " + " / ".join(add_ons) + ". Call it once, right away, with the subject the message gives; fill any field the message leaves open with a usual value instead of asking, and do not look anything up first. Then report the figure its result gives for that subject.")
    return notes


def guide_block(request: str, tools: Iterable) -> str:
    return "\n".join(guidance(request, tools))
