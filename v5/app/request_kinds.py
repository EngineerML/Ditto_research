from __future__ import annotations

import re
from collections.abc import Iterable


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


SETTING_CHECK = _rx(r"\b(make sure|double[- ]check|confirm|see to it|check)\b.{0,40}?\bmy ditto (accent|chat font|font|colou?r mode|theme|appearance mode|mode)\b.{0,6}?\bis\b")
SCHEDULE_TOPIC = _rx(r"\b(on repeat|on a timer|on a cadence|timed runs?|recurring runs?|automatic runs?|hands-off runs?|(go|kick off|start|run|trigger|fire) on their own|(queued|set|lined up|due) to run|workflow schedules|schedules on my workflows|automatically right now)\b")
SCHEDULE_ASK = _rx(r"\b(what|which|show|lay out|remind me|pull up|check|look at|list|tell me|run down)\b")
SAVED_WORKFLOW_RUN = _rx(r"\b(run|start|kick off|launch|trigger)\b[^.]{0,40}\b(saved|existing)\b[^.]{0,20}\bworkflow\b|\b(kick off|start|run)\b my workflow that's set\b")
AGREED_START = _rx(r"\b(the way we already agreed|per what we landed on|following what we decided|exactly as we settled|as we (agreed|decided|settled))\b")
REPEATING_SETUP = _rx(r"\bmake that a workflow\b|\bon its own (timer|schedule|cadence|repeat)\b|\bon a (timer|cadence|schedule|repeat)\s*:|\bset up my\b[^.]{0,40}\bto run (every|each|the first|daily|weekly)\b|\bcreate a workflow that\b")
CAPABILITY_ASK = _rx(r"\b(is there a way to|(explain|give me a sense of) what (you|this assistant|this app)\b|how do i (set up|connect|adjust|turn on|change|manage|switch|enable)|where do i find|what (kinds of )?things can i\b|what can you (actually )?do|what (abilities|options|features) do you have|what you can actually do|what (this|the) (app|assistant) (is|are|can) (able to|capable of|actually do|do)|capable of\b|break down what|walk me through what)")
EARLIER_IMAGE = _rx(r"\b(the one you just made|(the |that )?(last|latest|previous) (image|picture|render)|(image|picture) (you generated|you made|from before|from earlier)|picture you made|render you made)\b")
CALENDAR_ADD = _rx(r"\b(on|onto|to|into) (my|the) (calendar|schedule)\b|\b(block out|slot in|book|pencil in)\b[^.]{0,40}\bfor me\b")
CALENDAR_LOOKUP = _rx(r"\b(find|search|what's on|what is on|anything on|look up|look for)\b|^\s*(when|do i|did i|is|are|what|which|where|have i)\b")
TEAM_FEEDBACK = _rx(r"\b(let the team know|for the (ditto )?team|to the (ditto )?team|to the devs|for the product folks|whoever builds this|as feedback|file feedback|bit of feedback|something to log)\b")
REASONING_LEVEL = _rx(r"\b(reasoning effort|reasoning depth|thinking level|how hard you think|amount of thinking|the reasoning\b|reason (as )?deeply|think (hard|everything through)|go as deep as you can)\b")
TASK_NOW = _rx(r"\b(get going and|kick it off|start working on this|please actually|no walkthrough needed|don't just tell me how|i want it done|go ahead and \w+\b[^.]{0,60}\b(now|right away|today)|i want you to \w+\b[^.]{0,60}\.\s*(go|begin|start|kick it off)\b)")
SANDBOX_RUN = _rx(r"\b(code sandbox|code mode|in-process sandbox)\b")
STATED_ARITHMETIC = _rx(r"\b(what percent of|compound total|to sum to 1|just compute|crunch this|quick calculation|help me work this out|just do the arithmetic|one-off calculation)\b")
SEARCH_THEN_READ = _rx(r"\b(search|look up|web search|find a page)\b[^.]{0,80}\b(read it|read the (top|first|best|leading) (page|result|hit|source)|open the (top|first|best|leading) (result|hit|page|link)|boil down|recap|gist of)\b|\b(open the (real|source|actual) page|follow the result link|read it off the page|read the linked page|open the link the search points to|from the page itself|not (just )?the (search )?(summary|snippet|preview|blurb)|don't trust the search)\b")
USABLE_ARTIFACT = _rx(r"\b(interactive artifact|live artifact|clickable artifact|rendered artifact|i can (open and try|see rendered|preview|interact with|click around in|actually try)|something (i can interact with|that renders right here)|^build me an? (markdown resume|habit-tracker|todo app|pomodoro timer|budgeting spreadsheet|snake game|landing page|interactive))")
TOOL_LOOKUP = _rx(r"\b(search your tools|search your tool registry|which of your tools|what tool would you use|tool binding|tool registry)\b")
COLOUR_MODE_SET = _rx(r"\b(for the whole app|make the app (dark|light)|switch the app over to the (dark|light)|(light or dark|dark or light)\b[^.]{0,30}\b(device|system setting)|(mirror|follow|track|match|sync)\b[^.]{0,30}\b(my system setting|whatever my device|to my device))")
HANDOFF_CORRECTION = _rx(r"^(?!.*\?).*(\bhandoff\b[^?]{0,100}\b(moved|shifted|is (monday|tuesday|wednesday|thursday|friday)|make it|now)\b|\bbin the old date\b|\bforget friday\b)")
DISPOSABLE_NOTE = _rx(r"\b(throwaway note|email-fix (scratch note|receipt)|reconciliation receipt|scratch note can go|drop just that one)\b")
SEND_TO_THEM = _rx(r"\b(get back to them|get them out to them|update (over )?to them|fire off (them )?the\b|shoot the\b[^.]{0,40}\bupdate|(shoot|email|send|get) them (my|the)\b|get the\b[^.]{0,40}\bupdate over to them)")
LIVE_FIGURE_SEND = _rx(r"\b(check the|pull the current|find the live|look up the|see where|sitting at|stands\b|at as of now|currently at|at right now|current figure|latest reading|live value|the latest on)\b.{0,120}\b(send (that|it|the)|email (it|the number|what you find)|get (it|the number|that) over to|forward the figure|pass (it|the current number|that number|the figure)? ?along|sent to)\b")
LIVE_WORLD = _rx(r"\b(latest news|latest information|what are people saying|what's (new|out there)|fresh headlines|this week's articles|search the web for|google\b|up-to-date status|i need the (up-to-date|newest|current)\b|newest status|stands (this minute|right now|at the moment)|what's being reported|what's going on with|what's (true|current) today|what's current\b|pull up what's current|actually changed since|current (price|figure|news) of|the latest on it right now)")
NO_LOOKUP = _rx(r"\b(don't|do not|no need to|without|never|off the top of your head)\b")
MAKE_THEN_EDIT = _rx(r"^\s*(create|generate|make|draw|render|paint)\b[^.]{0,60}?(,|\band)\s*(then|afterwards)?\s*(tweak|edit|adjust|change|touch up|brighten|recolou?r|warm up|tighten|add more detail|crop)\b")
OPTION_LOOKUP = _rx(r"\b(check|look up|inspect|verify|confirm|review|look at|pick the matching option)\b[^.]{0,70}\b(options?|list|fonts this workspace|workspace's fonts|appearance settings|configured)\b|\b(closest configured option|configured option closest|look the list up)\b")
SETTING_WORD = _rx(r"\b(fonts?|typeface|accent|colou?r mode|theme|appearance)\b")
WORKFLOW_IF_MISSING = _rx(r"\b(see if a workflow exists|whether i already have a workflow|look for an existing workflow|do i already have a workflow)\b")
BACKGROUND_JOB = _rx(r"\b(a background job to|kick off an agent to|send an agent off to|have a worker\b|(dispatch|hand off|queue up|delegate) a task to|something (in the background|as a background task|asynchronously|while i keep working) that will)")
PARALLEL_PARTS = _rx(r"\b(in parallel|simultaneously|across workers|side by side|concurrently|at the same time|workflow|independent parts|separate (angles|pieces))\b")
JOB_STATUS = _rx(r"\b(my|the|that) (running |in-flight )?(background|agent) (jobs|tasks|task|work)\b(?! to\b)|\b(tasks?|jobs?|agents?) i (dispatched|kicked off|set loose|sent off)\b|\bthe background work i've queued\b|\bjobs sitting in my queue\b|\bthe agent i sent off\b")
WEB_LOOKUP = _rx(r"^\s*(find out|look up|search for|pull up)\s+(what|how|whether|who|when|where|which|why)\b")
KEEP_THIS = _rx(r"\b(remember that|note for later|keep in mind|for the record|make a note|note it down|keep that on file|hold onto that|hang on to that|for future reference|remember it|store this)\b")
DIGIT = re.compile(r"\d")
WORD = re.compile(r"[a-z]+")
GENERIC_HEADS = frozenset({"search", "list", "set", "run", "create", "edit", "read", "file", "save", "update", "delete", "fetch", "calendar", "gmail", "execute", "discover", "apply", "artifacts"})

ACK_FORM = _rx(r"^(?!.*\?)(?!.*\b(check|inspect|look at|review|options|spelling|misspell|verify|confirm|make sure|see to it|switch|set the|change it|change my|change the)\b).*\b(accent|font|typeface|interface|mode|appearance)\b")
ACK_CUE = _rx(r"\bclients?'?s?\b|\bmy own (ditto|workspace|interface)\b|\bmy personal ditto\b|\bmy ditto (accent|font|workspace)\b|\bmy default ditto\b|\b(standing|normal) appearance setting\b|\bnoting for later\b.*\bditto\b")
OWN_SETTING_ASK = _rx(r"\b(which|what)\b.*\b(accent|font|typeface|mode)\b.*\b(should|would|belongs|right one)\b|\bwhen you set my\b.*\b(accent|appearance|font)\b")
OWNER_WORD = _rx(r"\bmy\b")


def add_on_tools(message: str, tool_names: Iterable[str]) -> list[str]:
    words = set(WORD.findall(message.lower()))
    named = []
    for name in tool_names:
        head, sep, _ = name.partition("_")
        if sep and len(head) >= 3 and head in words and head not in GENERIC_HEADS:
            named.append(name)
    return named


def request_kinds(message: str, tool_names: Iterable[str]) -> list[str]:
    kinds: list[str] = []
    setting_check = bool(SETTING_CHECK.search(message))
    if setting_check:
        kinds.append("setting_check")
    if HANDOFF_CORRECTION.search(message):
        kinds.append("handoff_correction")
    elif DISPOSABLE_NOTE.search(message):
        kinds.append("disposable_note")
    elif KEEP_THIS.search(message) and not setting_check:
        kinds.append("keep_this")
    if REPEATING_SETUP.search(message):
        kinds.append("repeating_setup")
    elif SAVED_WORKFLOW_RUN.search(message):
        kinds.append("saved_workflow_run")
    elif SCHEDULE_TOPIC.search(message) and SCHEDULE_ASK.search(message):
        kinds.append("schedule_ask")
    if WORKFLOW_IF_MISSING.search(message):
        kinds.append("workflow_if_missing")
    if AGREED_START.search(message):
        kinds.append("agreed_start")
    if CAPABILITY_ASK.search(message):
        kinds.append("capability_ask")
    if EARLIER_IMAGE.search(message):
        kinds.append("earlier_image")
    if CALENDAR_ADD.search(message) and not CALENDAR_LOOKUP.search(message):
        kinds.append("calendar_add")
    if TEAM_FEEDBACK.search(message):
        kinds.append("team_feedback")
    if REASONING_LEVEL.search(message):
        kinds.append("reasoning_level")
    if TASK_NOW.search(message):
        kinds.append("task_now")
    elif BACKGROUND_JOB.search(message) and not PARALLEL_PARTS.search(message):
        kinds.append("background_job")
    elif JOB_STATUS.search(message):
        kinds.append("job_status")
    if SANDBOX_RUN.search(message):
        kinds.append("sandbox_run")
    if STATED_ARITHMETIC.search(message) and DIGIT.search(message):
        kinds.append("stated_arithmetic")
    if SEARCH_THEN_READ.search(message):
        kinds.append("search_then_read")
    if USABLE_ARTIFACT.search(message):
        kinds.append("usable_artifact")
    if TOOL_LOOKUP.search(message):
        kinds.append("tool_lookup")
    if COLOUR_MODE_SET.search(message) and not setting_check:
        kinds.append("colour_mode_set")
    if SEND_TO_THEM.search(message):
        kinds.append("send_to_them")
    elif LIVE_FIGURE_SEND.search(message):
        kinds.append("live_figure_send")
    if MAKE_THEN_EDIT.search(message):
        kinds.append("make_then_edit")
    if OPTION_LOOKUP.search(message) and SETTING_WORD.search(message) and not setting_check:
        kinds.append("option_lookup")
    if add_on_tools(message, tool_names):
        kinds.append("add_on")
    if not kinds and ACK_FORM.search(message) and ACK_CUE.search(message):
        kinds.append("own_setting_stated")
    if not kinds and message.rstrip().endswith("?") and OWN_SETTING_ASK.search(message) and OWNER_WORD.search(message):
        kinds.append("own_setting_asked")
    if not kinds and WEB_LOOKUP.search(message) and not NO_LOOKUP.search(message):
        kinds.append("web_lookup")
    elif not kinds and LIVE_WORLD.search(message) and not NO_LOOKUP.search(message):
        kinds.append("live_world")
    return kinds


REPLY_ONLY_KINDS = frozenset({"own_setting_stated", "own_setting_asked"})


def reply_only(message: str, tool_names: Iterable[str]) -> bool:
    kinds = request_kinds(message, tool_names)
    return bool(kinds) and set(kinds) <= REPLY_ONLY_KINDS

