from __future__ import annotations

from collections.abc import Iterable

import re

from .memory.people import SHORT_RECORD_CHARS, by_date
from .protocol import MemoryPair
from .request_kinds import add_on_tools, request_kinds, setting_named

SETTING_CHECK_NOTE = "About this request: it asks you to make sure one of the user's Ditto appearance settings (accent colour, chat font or colour mode) has a certain value. First find the user's note that keeps their own value for that same setting: it is among the notes shown with this message, so reading it needs no tool (no discover_capabilities call, no search). If that note already keeps the value the message names, nothing needs changing: make no call at all, not even a lookup, and reply that it is already set to that value, naming the value as the note writes it. If the note keeps a different value for that setting, the message is asking for a change, even where it says check or confirm: call the setter for that setting with the value the message names, rather than only reporting the difference. A note may call the setting something else (the chat font its typeface or interface font, the accent the app's colour, the colour mode its look) and it is the same setting; a value that differs by even one word is a different value (navy is not dark navy). That note is how you know the setting: never say you cannot read it."
SCHEDULE_NOTE = "About this request: it asks about the user's workflows that run by themselves at set times (recurring, timed or repeating). When each one runs and how many runs it has logged is what list_schedules returns: call list_schedules for it (list_workflows lists the saved workflows themselves, not their schedule), and answer from its result."
SAVED_WORKFLOW_NOTE = "About this request: to run a workflow the user has already saved, first call list_workflows to find it by the name or schedule the message gives, then call run_workflow passing only its name argument, exactly as list_workflows lists it, never its id or recipe_id."
AGREED_NOTE = "About this request: it asks to start work the user says was agreed earlier. Find the user's decision note about this project's work; it says how to run it: run an existing workflow (call list_workflows, then run_workflow with the workflow name exactly as the decision note writes it; if the list does not show it, still call run_workflow with that name in its name field, since another listed workflow is a different one), create a new reusable workflow with create_workflow under the name the note gives, or dispatch one one-off background job with execute_agent_job. Do what that note says and nothing else."
REPEATING_NOTE = 'About this request: it asks for something to happen on a repeating schedule: create it now with create_workflow, with the schedule and the action the message states; fill anything it leaves open, such as what exactly it covers, with a usual choice instead of asking. It needs no search of the notes first, and a note about the plan of some other project does not change it.'
CAPABILITY_NOTE = 'About this request: it asks what Ditto can do or how to do something in it, not for the thing to be done: change no setting and start nothing. Look it up with discover_capabilities first and answer from what it returns.'
EARLIER_IMAGE_NOTE = "About this request: it asks to change an image made earlier in this chat. There is no link for it and nothing about it in the notes: call edit_image right away with image_url set to the image as the user refers to it (for example 'the last image you made') and the change as the instruction, instead of asking for a link."
CALENDAR_LOOKUP_NOTE = "About this request: it asks whether something is on the user's calendar: look with calendar_search_events and answer from what it returns."
CALENDAR_NOTE = "About this request: it asks to put an event on the calendar. Read the user's notes about this event first. If a note says it is already on the calendar, find it with calendar_search_events and say where it is; do not add another. If you search and the result lists it, it is on the calendar: say so and add nothing. Where a note says it is already there, that holds whatever the search returns, even a bare 'Done' or no match: say it is there and add nothing. If a note says its date has not been decided yet, ask the user when, naming the event in the note's own words and spelling, and add nothing. In every other case, including when no day or time is given, create it right away with calendar_create_event: the title is the event's name as the message or the note gives it (never a reference code), and 'when' is the day or time the message or the note gives, or 'unscheduled' when neither gives one, since the user can move it later; do not ask when."
FEEDBACK_NOTE = "About this request: it is feedback meant for the Ditto team: file it with file_feedback_for_team, its text in the user's words. It is not an email to anyone."
REASONING_NOTE = 'About this request: it is about how much reasoning the user wants by default. When it states the level (deep or careful thinking is high, balanced or moderate is medium, quick or minimal is low), set it now with set_reasoning_effort. When it asks for the way they usually like it, use the default their note names; if their note says they have not picked one yet, ask which reasoning effort level they want as their default, naming the options the note mentions, and set nothing.'
TASK_NOW_NOTE = "About this request: it asks for a task to be carried out now rather than explained: start it with execute_agent_job, the task in the user's words, also when it is scraping or gathering something a web search could partly cover, even when the task is to build, scaffold or write code or an app (that work runs as an agent job, not as an artifact). The job itself finds the file, document or code the message mentions, even with nothing attached and no name or link given, so do not ask for it: the only reply to this message is that call."
SANDBOX_NOTE = 'About this request: Run it with run_code: a short snippet that calls the routine by the name the user gives, and report exactly what it prints. It is not a background job.'
ARITHMETIC_NOTE = 'About this request: it asks for arithmetic over figures it states: compute it with run_code (a short snippet) and report the result, even when the user says no script or project is needed; that only rules out building something bigger.'
SEARCH_THEN_READ_NOTE = "About this request: search with search_web, then open the top result's link with read_links and answer from that page. A search result shows only a preview of each page: open the link before you answer, even when the preview seems to answer already or looks off the subject. Search once; the top result is the one to open."
ARTIFACT_NOTE = 'About this request: it asks for something the user can open and use: build it with the artifacts tool, not as an image.'
TOOL_LOOKUP_NOTE = 'About this request: Look through the available tools with search_tools first and answer from what it finds, naming the tool. It asks which tool fits, so make no other call: do not go on to use the tool it finds, and do not search the web.'
COLOUR_MODE_NOTE = "About this request: it asks to set Ditto's colour mode now: call set_theme with dark or light as asked, or system when the app should follow, match or sync to the device (wording like \"light or dark mode to my device\" names no one mode: that is system), even if a note mentions another mode; the request is the current instruction."
HANDOFF_NOTE = 'About this request: it corrects a fact in a note the user saved earlier: the handoff scratchpad of the project the message names, the note that calls itself that project\'s handoff scratchpad, not the project\'s own records. Do not rewrite the whole note or save a new one. Call update_memory on that note\'s pair_id with short content that names the project and says what changed, with handoff as one word, for example: handoff is <the day the message gives>, for the "<project>" scratchpad; reviewer is <the name, where the message names a reviewer>'
DISPOSABLE_NOTE = 'About this request: it asks to delete one disposable note about a person (an email-fix receipt or scratch note) while keeping their contact record. Find that note itself: the one that calls itself a receipt or a scratch note, or says it can be deleted once reviewed, even where the message names it by what it was about ("the note about their email"). Delete only it with delete_memory, once, using its own pair_id exactly as the records give it (never a record mark or number). The record that states their email address, employer or role is one of the records that stay.'
SEND_TO_THEM_NOTE = "About this request: it asks to send numbers or an update to 'them', and asking for it now means it is ready to go. The user's note on this project says who gets it: the person who asked for it, if someone asked; otherwise the recipient the note plans for. Send it right away with gmail_send to that person's address; the body simply says the figures or the update are ready; do not ask the user for the numbers. Only if the note says the user has not yet decided who gets it, send nothing and ask who should get it, writing out in your question the project's name and each person the note names."
LIVE_FIGURE_NOTE = 'About this request: Look the figure up live with search_web first (it is not in the notes), then email what you found with gmail_send to that person, at the address their record gives.'
KEEP_THIS_NOTE = 'About this request: Save it with save_memory, then confirm what you saved, repeating the value in double quotation marks exactly as the user wrote it.'


MAKE_THEN_EDIT_NOTE = "About this request: it asks for a new image and then a change to it. Create it with create_image first, then call edit_image on the image that call returns, with the change as the instruction; a change the message leaves loose (such as tweak the colors) goes in in the message's own words, without asking how first."
OPTION_LOOKUP_NOTE = "About this request: it asks to set an appearance option whose name the user may have misspelled. List the options with discover_capabilities first; listing them sets nothing, so after it returns, make the setter call before you reply. Read the name the user wrote as the ordinary word it most likely stands for (a misspelt everyday colour or font name is that colour or font), and call the setter once with the listed option that is that word, or the variant of it the user names; a '-ish' or 'a bit' wording means the option named by all the words before it, so a misspelt word and then a colour is the two-word option, not the plain colour; 'the X version, variant or shade of Y' names the listed option made of both words (the blue version of sky is sky blue), not plain X or plain Y. Do not stop at the list: make the setter call. Say which option you used."
WORKFLOW_IF_MISSING_NOTE = "About this request: list the saved workflows with list_workflows first. The list only tells you whether one exists: make the create_workflow call before you reply when none is for this project. If none is for this project, create one with create_workflow named with the formal project name the user's records give, and put the reviewer's current email address, taken from their latest contact record, into the review step rather than only their name. The formal project name is the one a record says is the same project as the user's shorthand (Program ..., Campaign ..., Project ...), never the client's name or the shorthand. Once the list shows none for this project, your next step is the create_workflow call itself: no reply and no summary of the notes before it. A decision note about a different project does not apply to this one."
TOOL_PREFS_NOTE = "About this request: it sets which tools the user's chats use from now on. Call set_chat_tool_preferences now with the preference in the user's words; that call keeps it, so nothing is needed before it."
WORKFLOW_MAKE_NOTE = "About this request: it asks to make a workflow that can be run later. Call create_workflow now, with a step for each part of the work the message names; nothing has to be searched or looked up first, since the steps do that when it runs. Making it is the whole request: do not also run it unless the message asks for it to be run now; words on how its steps run, such as at the same time, describe the workflow."
LIVE_WORLD_NOTE = "About this request: it asks what is true in the world now. Look it up live with search_web, once, and answer from what it returns (results that do not help are a thing to say, not a reason to search again); the user's notes only show what they knew when they wrote them, and setting those notes aside is not a request to delete them."
BACKGROUND_JOB_NOTE = "About this request: it asks for a one-off task to run in the background while the user carries on: start it now with execute_agent_job, the task in the user's words."
JOB_STATUS_NOTE = "About this request: it asks how background jobs the user already started are doing: check them with list_agent_jobs and answer from what it returns, without starting anything new."
WEB_LOOKUP_NOTE = "About this request: it asks you to look up something the web can answer: call search_web for it and answer from what it returns."
OWN_SETTING_STATED_NOTE = 'About this request: the user is telling you their own Ditto appearance preference. Acknowledge it in one short sentence that says the value back as they wrote it ("pinkish red", not pinkish-red). This states a preference and asks for nothing to be done, even where it says keep or leave: make no call, change no setting, and do not say that nothing needed changing.'
OWN_SETTING_ASKED_NOTE = "About this request: it asks which value the user's own Ditto appearance preference holds for one setting (accent colour, interface font or colour mode). Their note may not name the setting: keeping their own interface in a typeface gives the font, what their Ditto appearance follows (light, dark or system) gives the colour mode, and a colour they like for Ditto itself gives the accent. Answer with that note's value as the note writes it; a value they turned down or a client's brand value is not theirs. Make no call."
NOTES = {
    "setting_check": SETTING_CHECK_NOTE,
    "handoff_correction": HANDOFF_NOTE,
    "disposable_note": DISPOSABLE_NOTE,
    "keep_this": KEEP_THIS_NOTE,
    "repeating_setup": REPEATING_NOTE,
    "saved_workflow_run": SAVED_WORKFLOW_NOTE,
    "schedule_ask": SCHEDULE_NOTE,
    "agreed_start": AGREED_NOTE,
    "capability_ask": CAPABILITY_NOTE,
    "earlier_image": EARLIER_IMAGE_NOTE,
    "calendar_add": CALENDAR_NOTE,
    "calendar_lookup": CALENDAR_LOOKUP_NOTE,
    "team_feedback": FEEDBACK_NOTE,
    "reasoning_level": REASONING_NOTE,
    "task_now": TASK_NOW_NOTE,
    "sandbox_run": SANDBOX_NOTE,
    "stated_arithmetic": ARITHMETIC_NOTE,
    "search_then_read": SEARCH_THEN_READ_NOTE,
    "usable_artifact": ARTIFACT_NOTE,
    "tool_lookup": TOOL_LOOKUP_NOTE,
    "colour_mode_set": COLOUR_MODE_NOTE,
    "send_to_them": SEND_TO_THEM_NOTE,
    "live_figure_send": LIVE_FIGURE_NOTE,
    "live_world": LIVE_WORLD_NOTE,
    "web_lookup": WEB_LOOKUP_NOTE,
    "background_job": BACKGROUND_JOB_NOTE,
    "job_status": JOB_STATUS_NOTE,
    "workflow_if_missing": WORKFLOW_IF_MISSING_NOTE,
    "workflow_make": WORKFLOW_MAKE_NOTE,
    "tool_prefs": TOOL_PREFS_NOTE,
    "make_then_edit": MAKE_THEN_EDIT_NOTE,
    "option_lookup": OPTION_LOOKUP_NOTE,
    "own_setting_stated": OWN_SETTING_STATED_NOTE,
    "own_setting_asked": OWN_SETTING_ASKED_NOTE,
}


def add_on_note(names: list[str]) -> str:
    return ("About this request: it names the listed add-on tool " + " / ".join(names) + ". Call it right away, passing the subject the message names; fill any required field the message leaves out with a usual value (a timer runs 25 minutes) instead of asking, "
            "and do not look up or ask for figures, phrases or links first. Its result may not label the figure as the code, id or number you asked for: the figure it states for the subject the message names is that answer, so give it exactly as written, not another figure from its output, and leave out what it says about anything else. The name you passed to it is not the answer: the answer is a figure from its output.")


# Said again right after the message, where a small model weighs it most.
CLOSING_LINES = {
    "setting_check": "If the user's note keeps a different value for this setting, call its setter with the value this message names, and only then reply; if it keeps this value, make no call.",
    "own_setting_stated": "Begin with 'Noted' and give the value as they wrote it, in one short sentence of your own, not their sentence again, and with nothing about what you can or cannot do.",
    "own_setting_asked": "Their note on this setting holds the value, also where it calls the setting by another word: give that value in one short sentence.",
    "capability_ask": "This asks whether or how something can be done, not for it to be done: answer from discover_capabilities and change nothing.",
}


def closing_lines(message: str, tool_names: Iterable[str]) -> str:
    return " ".join(CLOSING_LINES[kind] for kind in request_kinds(message, list(tool_names)) if kind in CLOSING_LINES)


def guidance(message: str, tool_names: Iterable[str]) -> list[str]:
    names = list(tool_names)
    return [add_on_note(add_on_tools(message, names)) if kind == "add_on" else NOTES[kind] for kind in request_kinds(message, names)]


def guide_block(message: str, tool_names: Iterable[str]) -> str:
    return "\n".join(guidance(message, tool_names))


# The words a note may use for each appearance setting a "make sure my Ditto X is Y" request names.
SETTING_WORDS = {
    "accent": re.compile(r"\baccent\b", re.I),
    "font": re.compile(r"\b(?:font|typeface)\b", re.I),
    "mode": re.compile(r"\b(?:colou?r mode|(?:dark|light|system) mode|theme|appearance)\b", re.I),
}
SETTING_LEAD_HEADER = "The user's own notes that mention this setting (their own value is the one they keep for themselves in Ditto; a client's or a brand's value is not theirs):"


def setting_lead(message: str, pairs: list[MemoryPair]) -> str:
    named = setting_named(message) or next((name for name in SETTING_WORDS if re.search(r"\b" + name, message, re.I)), "")
    if not named:
        return ""
    asked = [SETTING_WORDS[named]]
    notes = by_date([pair for pair in pairs if len(pair.prompt) < SHORT_RECORD_CHARS and asked[0].search(pair.prompt)])[-4:]
    if not notes:
        return ""
    return SETTING_LEAD_HEADER + "\n" + "\n".join(f"- {pair.timestamp[:10]}: {pair.prompt}" for pair in notes)


# After a listing of appearance options: the listed names nearest by letters to the words the message wrote.
OPTION_LIST_RE = re.compile(r"(accent colors|chat fonts):\s*([^;.]+)", re.IGNORECASE)
NEAREST_OPTIONS = 3
NEAREST_LINE = "\n\nThe listed {what} nearest by letters to the words of the message, nearest first, worked out by code and not checked: {names}. Set the first of them, unless the message names a variant, such as a shade or a style, that another of them holds."


def letters_alike(one: str, other: str) -> float:
    # Share of letters alike, where a slipped, missing, extra or swapped letter each counts as one edit.
    row_before: list[int] = []
    row = list(range(len(other) + 1))
    for at, letter in enumerate(one, start=1):
        row_before, row, last = row, [at] + [0] * len(other), row_before
        for place, against in enumerate(other, start=1):
            row[place] = min(row_before[place] + 1, row[place - 1] + 1, row_before[place - 1] + (letter != against))
            if at > 1 and place > 1 and letter == other[place - 2] and one[at - 2] == against:
                row[place] = min(row[place], last[place - 2] + 1)
    return 1 - row[-1] / max(len(one), len(other), 1)


def nearest_options(message: str, listing: str) -> str:
    font = bool(re.search(r"\b(?:font|typeface|chat)\b|\bf\w{1,3}nt\b", message, re.IGNORECASE))
    words = [word.lower() for word in re.findall(r"[A-Za-z]+", message)]
    for what, names in OPTION_LIST_RE.findall(listing):
        if ("font" in what.lower()) != font:
            continue
        scored = []
        for name in (part.strip() for part in names.split(",")):
            parts = name.lower().split()
            score = sum(max((letters_alike(part, word) for word in words), default=0.0) for part in parts) / max(1, len(parts))
            scored.append((score, name))
        scored.sort(key=lambda row: -row[0])
        return NEAREST_LINE.format(what=what.lower(), names=", ".join(name for _, name in scored[:NEAREST_OPTIONS]))
    return ""
