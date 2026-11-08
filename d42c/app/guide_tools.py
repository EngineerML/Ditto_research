from __future__ import annotations

import re
from collections.abc import Iterable

from .connectors import named_app_tools
from .request_kinds import add_on_tools, request_kinds

SETTING_CHECK_NOTE = "About this request: it asks you to make sure one of the user's Ditto appearance settings (accent colour, chat font or colour mode) has a certain value. Before any call, find the user's note that keeps their own value for that same setting and compare it with the value the message names. If the note already keeps that value, it is already set: reply that it is already set to that value, naming the value as the note writes it, and make no call at all, not even a lookup; calling the setter would change nothing, and making sure needs no call. If the note keeps a different value for that setting, call the setter for that setting with the value the message names."
SCHEDULE_NOTE = "About this request: it asks about the user's workflows that run by themselves at set times (recurring, timed or repeating). When each one runs and how many runs it has logged is what list_schedules returns: call list_schedules for it (list_workflows lists the saved workflows themselves, not their schedule), and answer from its result."
SAVED_WORKFLOW_NOTE = "About this request: to run a workflow the user has already saved, first call list_workflows to find it by the name or schedule the message gives, then call run_workflow with its name exactly as listed."
AGREED_NOTE = "About this request: it asks to start work the user says was agreed earlier. Find the user's decision note about this project's work; it says how to run it: run an existing workflow (call list_workflows, then run_workflow with the workflow name exactly as the decision note writes it; when the list does not show that workflow, its id is unknown, so pass that name in run_workflow's name field; another workflow in the list is a different one), create a new reusable workflow with create_workflow under the name the note gives, or dispatch one one-off background job with execute_agent_job. Do what that note says and nothing else."
REPEATING_NOTE = 'About this request: it asks for something to happen on a repeating schedule: create it now with create_workflow, with the schedule and the action the message states; fill anything it leaves open with a usual choice instead of asking.'
CAPABILITY_NOTE = 'About this request: it asks what Ditto can do or how to do something in it. Look it up with discover_capabilities first and answer from what it returns; it asks how, not for the change itself, so change no setting.'
EARLIER_IMAGE_NOTE = "About this request: it asks to change an image made earlier in this chat. If neither the message nor the notes give a link for it, call edit_image right away with image_url set to the image as the user refers to it (for example 'the last image you made') and the change as the instruction, instead of asking for a link."
CALENDAR_NOTE = "About this request: it asks to put an event on the calendar. Read the user's notes about this event first. If a note says it is already on the calendar, find it with calendar_search_events and say where it is; do not add another. If a note says its date has not been decided yet (no date yet, to be settled later, the user will say when), ask the user when, naming the event, and add nothing, even though the message asks to add it. In every other case, including when the message and the notes simply give no day or time, create it right away with calendar_create_event: the title is the event's name as the message or the note gives it (never a reference code), and 'when' is the day or time the message or the note gives, or 'unscheduled' when neither gives one, since the user can move it later; do not ask when."
CALENDAR_HELD_NOTE = "About this request: it asks whether something is on the user's calendar: look it up with calendar_search_events and answer from what it returns."
FEEDBACK_NOTE = "About this request: it is feedback meant for the Ditto team: file it with file_feedback_for_team, its text in the user's words. It is not an email to anyone."
REASONING_NOTE = "About this request: it is about how much reasoning the user wants by default. When it states the level (deep or careful thinking is high, balanced or moderate is medium, quick or minimal is low), set it now with set_reasoning_effort. When it asks for the way they usually like it, set it now with set_reasoning_effort to the default their note names; if their note says they have not picked one yet, set nothing and ask which reasoning effort level they want as their default, naming each option in the note's own words, copied as the note writes them, not as low, medium or high."
TASK_NOW_NOTE = "About this request: it asks for a task to be carried out now rather than explained: start it with execute_agent_job, the task in the user's words. That background job does the whole task itself (code, scripts, scraping, reports, apps), so the task goes to it even when a web search, a picture, an artifact or a script written into your reply could cover part of it; do not ask for files or links first."
SANDBOX_NOTE = 'About this request: Run it with run_code: a short snippet that calls the routine by the name the user gives, and report exactly what it prints. It is not a background job.'
ARITHMETIC_NOTE = 'About this request: it asks for arithmetic over figures it states: compute it with run_code (a short snippet) and report the result, even when the user says no script or project is needed; that only rules out building something bigger. When what the sandbox returns does not give the figures, that is all a run returns: give the figures the snippet works out in the reply, after any other call the message asks for.'
SEARCH_THEN_READ_NOTE = "About this request: search with search_web, then open the top result's link with read_links and answer from that page. A search result shows only a short preview of each page, and the preview is not the page: open the top link with read_links before you answer, even when the preview already seems to answer, and give the figures the page itself states."
ARTIFACT_NOTE = 'About this request: it asks for something the user can open and use: build it with the artifacts tool, not as an image.'
TOOL_LOOKUP_NOTE = 'About this request: Look through the available tools with search_tools first and answer from what it finds, naming the tool; it asks which tool fits, so leave the tool it finds unused.'
COLOUR_MODE_NOTE = "About this request: it asks to set Ditto's colour mode now: call set_theme with dark or light as asked, or system when the app should follow the device, even if a note mentions another mode; the request is the current instruction."
HANDOFF_NOTE = 'About this request: it corrects a fact in a note the user saved earlier: the handoff scratchpad of the project the message names, the note that calls itself that project\'s handoff scratchpad, not the project\'s own records. If that note is not among the records shown, find it with search_memories first. Call update_memory on that note\'s pair_id with short content that names the project and states only the corrected fact, for example: handoff for the "<project>" scratchpad is Wednesday; add the reviewer only when the message itself names one. Do not rewrite the whole note or save a new one.'
DISPOSABLE_NOTE = 'About this request: it asks to delete one disposable note about a person (an email-fix receipt or scratch note) while keeping their contact record. The note to delete is the receipt or scratch note itself, the one that calls itself a receipt or scratch note and says it can be deleted; a record saying they moved and giving their new work email is part of their contact history and stays. If that note is not among the records shown, find it with search_memories first. Then delete only it with delete_memory, using its pair_id; their contact, work and email records stay.'
SEND_TO_THEM_NOTE = "About this request: it asks to send numbers or an update to 'them', and asking for it now means it is ready to go. The user's note on this project says who gets it: the person who asked for it, if someone asked; otherwise the recipient the note plans for. Send it right away with gmail_send to that person's address; the body simply says the figures or the update are ready; do not ask the user for the numbers. Only if the note says the user has not yet decided who gets it, ask which of the people it names, and send nothing."
LIVE_FIGURE_NOTE = 'About this request: Look the figure up live with search_web first (a figure the notes give is not a live one), then email what you found with gmail_send to that person, at the address their record gives.'
KEEP_THIS_NOTE = 'About this request: Save it with save_memory, then confirm what you saved, repeating the value in double quotation marks exactly as the user wrote it.'
TOOL_PREFS_NOTE = "About this request: it sets which tools are used in the user's chats from now on. Call set_chat_tool_preferences right away with the preference in the user's words; that call itself keeps it as their default, so it needs nothing before it: no saved note and no tool search."
WORKFLOW_BUILD_NOTE = "About this request: it asks for a reusable workflow built from the goal it names: create it now with create_workflow, the goal in the user's words and its parts as steps, and fill anything it leaves open with a usual choice instead of asking. One create_workflow call makes the whole workflow."


SEARCH_AND_IMAGE_NOTE = "About this request: it asks for a web search and a new picture, each its own call: search the subject with search_web, and make a picture of that subject with create_image, its prompt naming the subject as the message words it. The picture does not depend on what the search returns: make both calls whatever the search finds, then reply with what the search says about the subject."
MAKE_THEN_EDIT_NOTE = "About this request: it asks for a new image and then a change to it. Create it with create_image first, then call edit_image on the image that call returns, with the change as the instruction."
OPTION_CHOICE_NOTE = "About this request: it asks to set an appearance option whose name the user may have misspelled. List the options with discover_capabilities first, then call the setter with the listed option that is closest to what they wrote, and say which option you used. When the message asks for a shade, variant, cut, edition or version of a name (the blue shade of that name, its sans cut), the option is the listed name made of that name followed by that word, not the plain name."
WORKFLOW_IF_MISSING_NOTE = "About this request: list the saved workflows with list_workflows first. If none is for this project, create one with create_workflow named with the formal project name the user's records give, and put the reviewer's current email address, taken from their latest contact record, into the review step rather than only their name. Their current email address is the one in the most recent record about how to reach them (after a move or a new job, the new one), and the review step gets that email address itself. If that record is not among the records shown, find it with search_memories first. A decision note about a different project does not apply to this one."
LIVE_WORLD_NOTE = "About this request: it asks what is true in the world now. Look it up live with search_web and answer from what it returns; the user's notes only show what they knew when they wrote them, and setting those notes aside is not a request to delete them. When what it returns does not speak of the thing asked, that is what the live source holds now: say so in the reply, after any other call the message asks for."
BACKGROUND_JOB_NOTE = "About this request: it asks for a one-off task to run in the background while the user carries on: start it now with execute_agent_job, the task in the user's words; the job itself works with what the task names, so do not ask for files or links first."
JOB_STATUS_NOTE = "About this request: it asks how background jobs the user already started are doing: check them with list_agent_jobs and answer from what it returns, without starting anything new."
WEB_LOOKUP_NOTE = "About this request: it asks you to look up something the web can answer: call search_web for it and answer from what it returns."
OWN_SETTING_STATED_NOTE = 'About this request: the user is telling you how they like their own Ditto appearance, a standing preference, not a request to change anything now. Make no call and change no setting. Acknowledge it in one short sentence in your own words that names the setting and gives only its value in double quotation marks, spelled as they wrote it, with its spaces and no hyphen added ("storm grey", not storm-grey). The value is the colour, the font name or the mode name alone, even when that name is an ordinary word. Never quote or repeat their sentence, and do not say that nothing needed changing.'
OWN_SETTING_ASKED_NOTE = "About this request: it asks which value the user's own Ditto appearance preference holds for one setting (accent colour, interface font or colour mode). Their note may not name the setting: keeping their own interface in a typeface gives the font, what their Ditto appearance follows (light, dark or system) gives the colour mode, and a colour they like for Ditto itself gives the accent. Answer with that note's value in double quotation marks exactly as the note writes it, with no hyphen added; a value they turned down or a client's brand value is not theirs. Make no call."
NOTES = {
    "setting_check": SETTING_CHECK_NOTE,
    "handoff_correction": HANDOFF_NOTE,
    "disposable_note": DISPOSABLE_NOTE,
    "keep_this": KEEP_THIS_NOTE,
    "tool_prefs": TOOL_PREFS_NOTE,
    "workflow_build": WORKFLOW_BUILD_NOTE,
    "repeating_setup": REPEATING_NOTE,
    "saved_workflow_run": SAVED_WORKFLOW_NOTE,
    "schedule_ask": SCHEDULE_NOTE,
    "agreed_start": AGREED_NOTE,
    "capability_ask": CAPABILITY_NOTE,
    "earlier_image": EARLIER_IMAGE_NOTE,
    "calendar_add": CALENDAR_NOTE,
    "calendar_held": CALENDAR_HELD_NOTE,
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
    "make_then_edit": MAKE_THEN_EDIT_NOTE,
    "search_and_image": SEARCH_AND_IMAGE_NOTE,
    "option_choice": OPTION_CHOICE_NOTE,
    "own_setting_stated": OWN_SETTING_STATED_NOTE,
    "own_setting_asked": OWN_SETTING_ASKED_NOTE,
}


CODE_TOOL = "run_code"


def runs_code(tool_name: str) -> bool:
    return tool_name == CODE_TOOL


SEARCH_TOOL = "search_web"


def searches_web(tool_name: str) -> bool:
    return tool_name == SEARCH_TOOL


SUMMARY_ASK = re.compile(r"\b(?:summar(?:y|ies|i[sz]e[sd]?|i[sz]ing)|digest)\b", re.I)
SUMMARY_SCOPE_NOTE = "The message asks for a summary: keep it to what the output says about the subject the message names; what the output says about anything else stays out of your reply."


def add_on_note(names: list[str], message: str = "") -> str:
    note = ("About this request: it names the listed add-on tool " + " / ".join(names) + ". Call it right away, passing the subject the message names; fill any required field the message leaves out with a usual value (a timer runs 25 minutes) instead of asking, "
            "and do not look up or ask for figures, phrases or links first. Its result may not label the figure as the code, id or number you asked for: the figure it states for the subject the message names is that answer, so give it exactly as written, not another figure from its output.")
    return note + " " + SUMMARY_SCOPE_NOTE if SUMMARY_ASK.search(message) else note


APP_NOTE = "About this request: it names {apps}, and the catalog lists that app's own tools ({tools}). When the message asks for something to be read from {apps} or done in it, make that one call now with the {apps} tool that does it, the one whose description names what the message says to look in or make there (a database, a board, a ticket, a channel); when none of its tools reads that one item, its listing or search tool is the one to call, with the name of the thing as its filter, since what it lists carries what the app holds about it. Answer from what it returns: a result can state figures for several things, and the answer is the figure it gives for the thing the message names, exactly as written, not another figure from it. Fill its fields from the message's own words; a field the message gives nothing for (a project, a post, a form, a filter) takes the name of the thing the message asks about, so do not ask the user for it first. If the result says the app is not connected, nothing was read or done there: tell the user so, and make no other call in its place. When {apps} is only where something was planned, kept or finished, or what a web search is about, make the call the message asks for (the email, the calendar event, the web search) and leave the tools of {apps} unused."


def app_note(named: dict[str, list[str]]) -> str:
    return APP_NOTE.format(apps=" / ".join(named), tools=", ".join(name for names in named.values() for name in names))


def note_for(kind: str, message: str, names: list[str]) -> str:
    if kind == "add_on":
        return add_on_note(add_on_tools(message, names), message)
    if kind == "app_named":
        return app_note(named_app_tools(message, names))
    return NOTES[kind]


def guidance(message: str, tool_names: Iterable[str]) -> list[str]:
    names = list(tool_names)
    return [note_for(kind, message, names) for kind in request_kinds(message, names)]


def guide_block(message: str, tool_names: Iterable[str]) -> str:
    return "\n".join(guidance(message, tool_names))
