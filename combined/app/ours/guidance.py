"""Advisory notes for the action lane, chosen from the request's wording and the tools it offers.

Each note describes how a careful assistant handles one kind of request with the tools at hand. A
note appears only when the request reads as that kind and the catalog offers the tool it names; the
deciding model still sees the whole request, the records and the whole catalog, and makes every call
and writes every answer itself. Nothing here removes, forces or rewrites anything.

The cues are mostly the shapes of a request ("set to run", "I can see rendered", "as we agreed")
rather than single content words, so a misspelled noun does not lose the note; where a noun is the
cue (calendar, picture), the pattern allows the letters around it to vary.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

WORD = re.compile(r"[A-Za-z][A-Za-z']*")


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


DAY = r"(?:mon|tues|wednes|thurs|fri|satur|sun)day"
# a word that starts like "calendar" and ends in r, with a letter or two astray ("calemdar", "caeendar")
CALENDAR_WORD = r"c[ae][a-z]{3,6}r"
PICTURE_WORD = r"(?:p[a-z]{0,2}c[a-z]{2,4}|image|imag|photo|render|drawing)"

# A setting check: an ask to make sure the user's own setting has a value (not a statement of it).
SETTING_ASK = _rx(r"\b(?:make sure|ensure|check|chec?k that|confirm|verify|see to it|double[- ]check)\b|\bm\w{1,3}e sure\b|\bch\w{1,3}k that\b")
OWN_SETTING = _rx(r"\bmy\b[^.?!]{0,30}\b(?:accent|font|fnot|typeface|theme|colou?r\s*m\w{2,3}|colr m\w{2,3}|mode|appearance)\b[^.?!]{0,30}\b(?:is|stays|set to)\b")
# A fact in a saved note that has changed.
CORRECTION = _rx(r"\b(?:moved|mo\w?ed|shifted|sh\w{2,3}ed|changed|is now|now on|instead of|scratch that|old date|forget " + DAY + r")\b"
                 r"|\bis " + DAY + r" now\b|\bmake it " + DAY + r"\b|\b(?:fix|correct|update|amend)\b[^.?!]{0,30}\b(?:note|what's there|entry|record)\b")
NOTE_WORDS = _rx(r"\bnotes?\b|\bscratch\w*\b|\brecord\b|\bentry\b|\bhandoff\b")
DELETE = _rx(r"\b(?:delete|remove|clear|c\wear|drop|get rid of|toss|discard|clean up|cl\w{2}n up|clutter|cl\w{2,3}ter|can go|is stale)\b|\bbin (?:the|that|this|it)\b(?! old date)")
DISPOSABLE = _rx(r"\b(?:receipt|rece\w{2,4}|scratch note|throwaway|th\w{3,4}away|temporary|disposable|leftover|email-fix|no longer needed)\b")
# An image made earlier in the chat: "that picture you made", "the image from earlier".
EARLIER_IMAGE = _rx(r"\b(?:that|the|this)\s+" + PICTURE_WORD + r"\s+(?:you\s+\w{2,8}|from\s+(?:before|earlier)|we\s+made)\b"
                    r"|\b(?:last|latest|previous|earlier)\s+" + PICTURE_WORD + r"\b|\bthe one you (?:just )?made\b")
SEND = _rx(r"\b(?:send|email|mail|forward|f\w{2}ward|pass|get|shoot|fire off|deliver|share)\b")
TO_THEM = _rx(r"\b(?:over to them|back to them|along to them|out to them|them (?:my|the|our) (?:[\w'\x22“”-]+ ){0,5}?(?:update|numbers|figures|summary|report|news))\b")
CALENDAR_PUT = _rx(r"\b(?:on|onto|onfo|to|into|imto|in)\s+(?:my|the)\s+" + CALENDAR_WORD + r"\b|\bslot (?:it|that) in\b|\bslot it\b|\bbl\w{2}k (?:out|off)\b")
CALENDAR_LOOKUP = _rx(r"^\W*(?:find|search|look (?:up|for)|what's on|what is on|is there|when is|when's|do i have|have i got)\b")
UNNAMED = _rx(r"\b(?:that|it|this|them)\s+(?:on|onto|to|into|in)\s+(?:my|the)\s+" + CALENDAR_WORD + r"\b")
# Workflows that run by themselves, asked about.
SCHEDULE_CUE = _rx(r"\b(?:schedul\w*|sc\w{2,3}ul\w*|recurring|repeating|on a timer|on a t\w{3,4}r|timed runs?|on their own|hands[- ]off|on (?:a )?cadence|set to run|due to run|lined up to run|runs? (?:daily|weekly|twice|every))\b")
SCHEDULE_ASK = _rx(r"\b(?:what|which|whatever|remind me|show|list|pull up|look at|check|tell me|run down|how many)\b|\?")
WORKFLOW = _rx(r"\bworkflows?\b|\bw\w{2,4}flows?\b")
RUN_VERB = _rx(r"\b(?:run|start|kick off|launch|trigger|fire)\b")
SAVED = _rx(r"\b(?:saved|existing|exis\w+|already|my workflow)\b")
# Something to happen again and again by itself, being set up.
REPEAT_CUE = _rx(r"\bon (?:its|their) own (?:repeat|timer|schedule|cadence)\b|\bon repeat\b|\bevery (?:day|morning|evening|week|month|weekday|" + DAY + r")\b"
                 r"|\b(?:daily|weekly|monthly) at\b|\beach (?:morning|evening|week|" + DAY + r")\b")
SETUP_VERB = _rx(r"\b(?:set up|have|make|create|schedule|arrange|get)\b")
# Work agreed earlier, to be started now.
AGREED = _rx(r"\b(?:per what we|as we (?:agreed|decided|settled|landed)|what we (?:agreed|decided|settled|landed) on|way we (?:\w+ )?(?:agreed|decided|settled)|following what we|fol\w+ what we)\b")
# A piece of work to carry out now, not explain.
DO_NOW = _rx(r"\b(?:start working|start it|get (?:it )?(?:going|started)|carry (?:it )?out|do (?:it|this) now|right away|kick it off|actually do|don't just tell me|i want it done)\b")
EFFORT = _rx(r"\b(?:reasoning|rea\w{2,5}ing depth|how (?:hard|deeply|much) you think|think (?:hard|harder|deeply|it through|things through)|thinking (?:level|depth|effort)|deep as \w+ can)\b")
TOOL_SWITCH = _rx(r"\b(?:disable|enable|turn (?:on|off)|switch (?:on|off)|stop using|don't use|do not use|allow|block|adjust|limit)\b[^.?!]{0,40}\b(?:tools?|web search|search(?:ing)? the web|image (?:making|generation))\b|\b(?:tools?|web search)\b[^.?!]{0,30}\b(?:off|disabled|enabled)\b")
TOOL_ASK = _rx(r"\b(?:which (?:of your )?tools?|what tool|tool binding|right tool|tool for|search your tools)\b")
CAPABILITY_ASK = _rx(r"\bhow (?:do|can) i (?:set up|connect|adjust|turn (?:on|off)|change|manage|switch|enable|disable|control)\b|\bwhere (?:do|can) i (?:find|change|set|turn|manage)\b|\bwhat (?:kinds? of )?\w+ can i ask\b|\bwhat can you (?:actually )?do\b|\bcapable of\b|\bwhat (?:features|options|abilities) do you have\b|\bis there a way to\b|\bwhat (?:this|the) (?:assistant|app) (?:can|does)\b")
# Something to open and use on screen.
USABLE = _rx(r"\bi can (?:see|open|click|cl\w{1,3}k|try|play|use|preview|interact)\b|\brendered\b|\binteractive\b|\b(?:game|landing page|web page)\b")
BUILD_VERB = _rx(r"\b(?:build|make|mock up|create|put together|draft)\b")
LIVE = _rx(r"\b(?:latest|right now|currently|current|today|these days|at the moment|as of now|live|stands|at right now|where is)\b")
PASS_ON = _rx(r"\b(?:get|send|email|forward|f\w{2}ward|pass|shoot)\b[^.?!]{0,40}\b(?:over to|along to|to)\s+(?:[A-Z][a-z]+|them|thm)\b|\bsent to [A-Z][a-z]+\b|\bfor [A-Z][a-z]+ —")
DEVICE = _rx(r"\b(?:device|system setting|operating system|phone|laptop)\b|\bsystem\b(?!\s+mode)")
APPEARANCE = _rx(r"\b(?:accent|font|typeface|theme|colou?r m\w{2,3}|dark mode|light mode|appearance|light or dark|dark or light)\b")
KEEP = _rx(r"\b(?:remember that|note (?:for later|it down|that)|keep in mind|for the record|hold on(?:to)? that|store this|save this)\b")
SANDBOX = _rx(r"\b(?:code sandbox|sandbox|run the routine|execute the routine)\b")
READ_PAGE = _rx(r"\b(?:open|read)\b[^.?!]{0,30}\b(?:page|source|link|article|site|result|hit)\b|\bread it\b|\bnot the (?:search )?(?:snippet|preview|summary|blurb)\b"
                r"|\b(?:boil|b\w{2,3}l) d\w{2,3}n\b|\bgist of\b|\bfirst source\b")
# A setting value named loosely: an "-ish" value, a spelling caveat, or a cut of a font.
LOOSE_NAME = _rx(r"\b(?:loosely|approximate|closest|matching option|my spelling|the spelling|mangled)\b|\w-ish\b|\b(?:edition|cut|variant) of\b"
                 r"|\b(?:check|verify|confirm|look up)\b[^.?!]{0,40}\b(?:options?|fonts?|f\w{3}s|accents?|list|configured|available)\b")
SETTING_WORD = _rx(r"\b(?:accent|acc\w{2,4}t|font|f\w{2,3}t|f\w{3}s|typ\w{1,3}face|chat|colou?r|theme)\b")
# asking which address or email a person has: a records question, not a figure to send
EMAIL_ASK = _rx(r"\b(?:which|what|wh[a-z]{2,4}|w[a-z]h[a-z]{1,3})\b[^.?!]{0,60}\b(?:email|address)\b|\b(?:current|up-to-date|right) email\b"
                r"|\bemail (?:reaches|belongs|is current)\b|\bemail\b[^.?!]{0,30}\bthese days\b")
# asking what has changed out in the world since an old note: a live lookup, not a note to correct
CHANGED_SINCE = _rx(r"\bwhat(?:'s| has| have)?\b[^.?!]{0,20}\bchanged\b")
# a run of figures the message itself lists ("312, 980, and 1510"), not dates or ids around a record
FIGURE_LIST = re.compile(r"(?<![\w-])\d+(?:\.\d+)?\s*(?:,\s*(?:and\s+)?|\s+and\s+)\d+(?:\.\d+)?(?![\w-])")
WORK_OUT = _rx(r"\b(?:mean|me\w{1,3}n|average|sum|normali[sz]e|fractions?|percent\w*|ratio|difference|how far apart|split|divide|multiply|add up|median|range|work (?:this|it) out)\b")
CRAWL = _rx(r"\b(?:scrape|scr\w{2}pe|crawl)\b")
JOB_LIST = _rx(r"\bjobs? list\b|\blist of (?:my )?jobs\b|\bmy [\w'-]+ (?:crawl|scrape|research|agent) job\b")

STAYING = ("Working out figures",)
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
    asks = "?" in text
    notes: list[str] = []
    setting = bool(SETTING_ASK.search(text) and OWN_SETTING.search(text)) and bool(offered & {"set_accent_color", "set_chat_font", "set_theme"})
    if setting:
        notes.append("Checking a setting: the message asks you to make sure one of the user's own settings (accent colour, chat font or colour mode) has a value. Read the user's note that keeps their value for that setting first. If it already keeps the value the message names, nothing needs changing: make no call at all, not even a lookup, and say it is already set, quoting the value as the note writes it. If the note keeps another value, or no note keeps a value for that setting, call that setting's setter with the value the message names.")
    correcting = "update_memory" in offered and bool(CORRECTION.search(text) and NOTE_WORDS.search(text)) and not DELETE.search(text) and not asks and not CHANGED_SINCE.search(text)
    if correcting:
        notes.append("Correcting a saved note: change the note the message means with update_memory on its pair id; when the message names a kind of note (a scratchpad, a list, a note for a person), it is that note, not another record about the same project. The new content replaces the whole note, so start it with the note's own opening words up to its first colon, which say what the note is for (its project and client), then the corrected facts, a few words each: the thing as the message calls it and its new value (as in 'handoff is Thursday'), plus 'reviewer is <name>' or the like for any other fact the message changes. Leave out the rest of the old text, and do not add a second note or touch other records.")
    if "delete_memory" in offered and DELETE.search(text) and DISPOSABLE.search(text):
        notes.append("Deleting one note: remove only the note the message points at, with delete_memory on that note's own pair id, which the records above show (do not ask the user for it). The person's other records (their contact, workplace or email notes) stay, even when the note mentions them.")
    if "edit_image" in offered and EARLIER_IMAGE.search(text):
        notes.append("Changing an earlier image: the message means an image made earlier in this conversation. It has no link and needs none: call edit_image right away with image_url naming it as the user does (for example 'the last image you made') and the change as the instruction. Do not ask for a link or a file, and do not make a new image.")
    if "gmail_send" in offered and SEND.search(text) and TO_THEM.search(text):
        notes.append("Sending to 'them': the message leaves the recipient as 'them'. The user's note on this project says who it goes to: whoever requested it, if anyone did, otherwise the recipient the note plans for. Send it right away with gmail_send to that person's email address exactly as their record gives it (a name alone is not an address); the body says the update or figures are ready. If the note says nobody has been chosen yet, send nothing and ask who should get it, naming the people the note mentions.")
    elif {"search_web", "gmail_send"} <= offered and LIVE.search(text) and PASS_ON.search(text) and not EMAIL_ASK.search(text):
        notes.append("Looking up a figure and sending it: the figure is live, not in the notes. Look it up with search_web first, then send it with gmail_send to the person the message describes, at the email address their records give (a later correction replaces an older address). Put the figure in the email exactly as the result writes it, and repeat it in your reply.")
    if "calendar_create_event" in offered and CALENDAR_PUT.search(text) and not UNNAMED.search(text) and not CALENDAR_LOOKUP.search(text):
        notes.append("Adding to the calendar: read the user's notes about this event first. If a note says the event is booked already, find it with calendar_search_events by its name and say where it is; do not add it again. Only if a note says its date is still undecided, add nothing and ask when, naming the event as the note does. In every other case create it right away with calendar_create_event, titled with the event's name: a day the message gives is used as given (the coming one), and when no day or time is given the time is left unscheduled; do not ask which day, week or time.")
    scheduled = SCHEDULE_CUE.search(text) and (SCHEDULE_ASK.search(text) or WORKFLOW.search(text)) and not EMAIL_ASK.search(text)
    run_saved = RUN_VERB.search(text) and WORKFLOW.search(text) and SAVED.search(text) and not asks
    # "set up X on repeat" is a new workflow; "pull up whatever is set to run on repeat" is a listing
    if "list_schedules" in offered and scheduled and not run_saved and not CAPABILITY_ASK.search(text) and not (REPEAT_CUE.search(text) and SETUP_VERB.search(text) and not asks):
        notes.append("Workflows that run on their own: which saved workflows run on a schedule, when they run and how many runs they have logged is what list_schedules returns (list_workflows lists the workflows themselves, not their schedules). Call list_schedules and answer from it.")
    if {"list_workflows", "run_workflow"} <= offered and run_saved:
        notes.append("Running a saved workflow: call list_workflows, pick the workflow whose name or schedule matches the message, then call run_workflow with its name exactly as listed (not its id).")
    if "create_workflow" in offered and REPEAT_CUE.search(text) and SETUP_VERB.search(text) and not asks and not SAVED.search(text):
        notes.append("Setting up something that repeats: the message wants it to happen again and again by itself. Create it now with create_workflow, with the schedule and the action the message states, filling anything it leaves open with a usual choice instead of asking. It is not a one-off job and not a note.")
    if AGREED.search(text) and offered & {"run_workflow", "create_workflow", "execute_agent_job"}:
        notes.append("Starting work agreed earlier: the user's note on this piece of work says how it was agreed to run: as one of their saved workflows (list_workflows, then run_workflow with the workflow name the note gives, even when the list does not show it: the run's result says whether it exists), as a new repeating workflow (create_workflow), or as a one-off job (execute_agent_job). Read that note and start it that way now.")
    elif "execute_agent_job" in offered and (DO_NOW.search(text) or (CRAWL.search(text) and not asks)):
        notes.append("Doing a task now: the message asks for a piece of work to be carried out now, not explained. Start it with execute_agent_job, the task in the user's words; do not ask for files or links and do not look up jobs or workflows first.")
    if "set_reasoning_effort" in offered and EFFORT.search(text):
        notes.append("Reasoning depth: how deeply you should think is set with set_reasoning_effort, once, with one of the values its schema lists: thinking hard, deep or thorough is high, balanced or moderate is medium, quick or minimal is low. If the message asks for the user's usual level, use the level their note names; if the note says they have not settled on one, ask which they want, naming the options the note mentions.")
    tool_prefs = "set_chat_tool_preferences" in offered and bool(TOOL_SWITCH.search(text)) and not asks
    if tool_prefs:
        notes.append("Which tools you may use: turning tools on or off for this chat (web search, image making and the like) is a setting, changed with set_chat_tool_preferences. Call it with the change the message asks for; it is not a search for a tool.")
    # "how do I manage which tools you can use" is a question about Ditto itself, not a tool search
    if "search_tools" in offered and TOOL_ASK.search(text) and not CAPABILITY_ASK.search(text) and not tool_prefs:
        notes.append("Finding a tool: the message asks which of your tools fits a job. Look with search_tools and answer from what it finds; make no other call, not even a web search.")
    if "discover_capabilities" in offered and CAPABILITY_ASK.search(text):
        notes.append("Asking what Ditto can do: questions about Ditto's own settings, features and abilities are answered from discover_capabilities. Call it first and answer from what it returns, not from the notes, and do not describe menus or steps from what apps usually have.")
    if "artifacts" in offered and USABLE.search(text) and BUILD_VERB.search(text):
        notes.append("Something to open and use: the message wants a thing it can see, click or try on screen. Build it with the artifacts tool, not as an image.")
    if "set_theme" in offered and APPEARANCE.search(text) and DEVICE.search(text) and not setting:
        notes.append("Colour mode: following or matching the user's device or system is the theme value 'system'. Set it directly with set_theme; no lookup is needed first.")
    if "save_memory" in offered and KEEP.search(text) and not correcting:
        notes.append("Saving a note: save what the user said with save_memory directly; there is no need to search the notes first. Then confirm what you saved, quoting it as the user wrote it.")
    if "run_code" in offered and SANDBOX.search(text):
        notes.append("Running code: run it once with run_code, a short snippet that calls the routine by the name the user gives, and report exactly what it prints; no web search or background job is needed.")
    if "list_agent_jobs" in offered and JOB_LIST.search(text):
        notes.append("The user's jobs: how far a job the user started got, and what it found, is what list_agent_jobs returns. Call it, find the job by the name the message gives, and answer with the figure it lists; the web does not have it.")
    elif {"search_web", "read_links"} <= offered and READ_PAGE.search(text):
        notes.append("Reading a page: search once with search_web, then open the top result's link exactly as it was returned with read_links, and answer from the page itself, since search previews can carry different figures. One search and one read are enough.")
    if "discover_capabilities" in offered and any(name.startswith("set_") for name in offered) and LOOSE_NAME.search(text) and SETTING_WORD.search(text) and not setting:
        notes.append("Choosing a listed option: the message names a setting's value loosely or misspelled (a font, a colour, a mode). List the options with discover_capabilities. When the message names a kind of a name (a variant, cut, edition, shade or version of it), the choice is the listed option made of that name and that word, not the plain name. Otherwise choose the listed option that needs the fewest single-letter changes to match the message's spelling, the first letter included. Then call the setter with it: both calls are needed.")
    if "run_code" in offered and FIGURE_LIST.search(text) and WORK_OUT.search(text) and not SANDBOX.search(text):
        notes.append("Working out figures: the message gives the figures and asks for a result worked out from them. Run the arithmetic once with run_code, even when the sum looks easy: the code tool is how calculations are done here. One run is enough whatever its output shows; then give the result.")
    add_ons = add_on_tools(request, names)
    if add_ons:
        notes.append("Named add-on tool: the message names the listed tool " + " / ".join(add_ons) + ". Call it once, right away, with the subject the message gives; fill any field the message leaves open with a usual value instead of asking, and do not look anything up first. Then report the figure its result gives for that subject, quoted exactly, even when the result names it differently from the message (an id or number the message asks for may come back as the subject's figure); leave out figures it gives for other things.")
    return notes


def guide_block(request: str, tools: Iterable) -> str:
    return "\n".join(guidance(request, tools))


def moves_to_action(request: str, tools: Iterable) -> bool:
    """A request one of the notes is for belongs on the action lane, where the notes are shown. The
    broad note on figures to work out is the exception: its cues alone are too common in questions
    about the records to move a request off the records lane. Setting checks move
    too: the records lane shows no notes and set the value even when it already matched."""
    return any(not note.startswith(STAYING) for note in guidance(request, tools))
