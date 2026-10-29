from __future__ import annotations

from collections.abc import Iterable

from .request_kinds import add_on_tools, request_kinds

SETTING_CHECK_NOTE = "About this request: it asks you to make sure one of the user's Ditto appearance settings (accent colour, chat font or colour mode) has a certain value. First find the user's note that keeps their own value for that same setting. If that note already keeps the value the message names, nothing needs changing: make no call at all, not even a lookup, and reply that it is already set to that value, naming the value as the note writes it. If the note keeps a different value for that setting, call the setter for that setting with the value the message names."
SCHEDULE_NOTE = "About this request: it asks about the user's workflows that run by themselves at set times (recurring, timed or repeating). When each one runs and how many runs it has logged is what list_schedules returns: call list_schedules for it (list_workflows lists the saved workflows themselves, not their schedule), and answer from its result."
SAVED_WORKFLOW_NOTE = "About this request: to run a workflow the user has already saved, first call list_workflows to find it by the name or schedule the message gives, then call run_workflow with its name exactly as listed."
AGREED_NOTE = "About this request: it asks to start work the user says was agreed earlier. Find the user's decision note about this project's work; it says how to run it: run an existing workflow (call list_workflows, then run_workflow with the workflow name exactly as the decision note writes it), create a new reusable workflow with create_workflow under the name the note gives, or dispatch one one-off background job with execute_agent_job. Do what that note says and nothing else."
REPEATING_NOTE = 'About this request: it asks for something to happen on a repeating schedule: create it now with create_workflow, with the schedule and the action the message states; fill anything it leaves open with a usual choice instead of asking.'
CAPABILITY_NOTE = 'About this request: it asks what Ditto can do or how to do something in it. Look it up with discover_capabilities first and answer from what it returns.'
EARLIER_IMAGE_NOTE = "About this request: it asks to change an image made earlier in this chat. There is no link for it and nothing about it in the notes: call edit_image right away with image_url set to the image as the user refers to it (for example 'the last image you made') and the change as the instruction, instead of asking for a link."
CALENDAR_NOTE = "About this request: it asks to put an event on the calendar. Read the user's notes about this event first. If a note says it is already on the calendar, find it with calendar_search_events and say where it is; do not add another. If a note says its date has not been decided yet, ask the user when, naming the event, and add nothing. In every other case, including when no day or time is given, create it right away with calendar_create_event: the title is the event's name as the message or the note gives it (never a reference code), and 'when' is the day or time the message or the note gives, or 'unscheduled' when neither gives one, since the user can move it later; do not ask when."
FEEDBACK_NOTE = "About this request: it is feedback meant for the Ditto team: file it with file_feedback_for_team, its text in the user's words. It is not an email to anyone."
REASONING_NOTE = 'About this request: it is about how much reasoning the user wants by default. When it states the level (deep or careful thinking is high, balanced or moderate is medium, quick or minimal is low), set it now with set_reasoning_effort. When it asks for the way they usually like it, use the default their note names; if their note says they have not picked one yet, ask which reasoning effort level they want as their default, naming the options the note mentions, and set nothing.'
TASK_NOW_NOTE = "About this request: it asks for a task to be carried out now rather than explained: start it with execute_agent_job, the task in the user's words; do not ask for files or links first."
SANDBOX_NOTE = 'About this request: Run it with run_code: a short snippet that calls the routine by the name the user gives, and report exactly what it prints. It is not a background job.'
ARITHMETIC_NOTE = 'About this request: it asks for arithmetic over figures it states: compute it with run_code (a short snippet) and report the result, even when the user says no script or project is needed; that only rules out building something bigger.'
SEARCH_THEN_READ_NOTE = "About this request: search with search_web, then open the top result's link with read_links and answer from that page."
ARTIFACT_NOTE = 'About this request: it asks for something the user can open and use: build it with the artifacts tool, not as an image.'
TOOL_LOOKUP_NOTE = 'About this request: Look through the available tools with search_tools first and answer from what it finds.'
COLOUR_MODE_NOTE = "About this request: it asks to set Ditto's colour mode now: call set_theme with dark or light as asked, or system when the app should follow the device, even if a note mentions another mode; the request is the current instruction."
HANDOFF_NOTE = 'About this request: it corrects a fact in a note the user saved earlier: the handoff scratchpad of the project the message names, the note that calls itself that project\'s handoff scratchpad, not the project\'s own records. Call update_memory on that note\'s pair_id with short content that names the project and states only the corrected fact, for example: handoff for the "<project>" scratchpad is Wednesday; add the reviewer only when the message itself names one. Do not rewrite the whole note or save a new one.'
DISPOSABLE_NOTE = 'About this request: it asks to delete one disposable note about a person (an email-fix receipt or scratch note) while keeping their contact record. Find that note itself, the one about the email fix or the receipt, and delete only it with delete_memory, using its pair_id; their contact, work and email records stay.'
SEND_TO_THEM_NOTE = "About this request: it asks to send numbers or an update to 'them', and asking for it now means it is ready to go. The user's note on this project says who gets it: the person who asked for it, if someone asked; otherwise the recipient the note plans for. Send it right away with gmail_send to that person's address; the body simply says the figures or the update are ready; do not ask the user for the numbers. Only if the note says the user has not yet decided who gets it, ask which of the people it names, and send nothing."
LIVE_FIGURE_NOTE = 'About this request: Look the figure up live with search_web first (it is not in the notes), then email what you found with gmail_send to that person, at the address their record gives.'
KEEP_THIS_NOTE = 'About this request: Save it with save_memory, then confirm what you saved, repeating the value in double quotation marks exactly as the user wrote it.'


MAKE_THEN_EDIT_NOTE = "About this request: it asks for a new image and then a change to it. Create it with create_image first, then call edit_image on the image that call returns, with the change as the instruction."
OPTION_LOOKUP_NOTE = "About this request: it asks to set an appearance option whose name the user may have misspelled. List the options with discover_capabilities first, then call the setter with the listed option that is closest to what they wrote (and the variant they name, if any), and say which option you used."
WORKFLOW_IF_MISSING_NOTE = "About this request: list the saved workflows with list_workflows first. If none is for this project, create one with create_workflow named with the formal project name the user's records give, and put the reviewer's current email address, taken from their latest contact record, into the review step rather than only their name. A decision note about a different project does not apply to this one."
LIVE_WORLD_NOTE = "About this request: it asks what is true in the world now. Look it up live with search_web and answer from what it returns; the user's notes only show what they knew when they wrote them, and setting those notes aside is not a request to delete them."
BACKGROUND_JOB_NOTE = "About this request: it asks for a one-off task to run in the background while the user carries on: start it now with execute_agent_job, the task in the user's words."
JOB_STATUS_NOTE = "About this request: it asks how background jobs the user already started are doing: check them with list_agent_jobs and answer from what it returns, without starting anything new."
WEB_LOOKUP_NOTE = "About this request: it asks you to look up something the web can answer: call search_web for it and answer from what it returns."
OWN_SETTING_STATED_NOTE = 'About this request: the user is telling you their own Ditto appearance preference. Acknowledge it in one short sentence that repeats the value in double quotation marks exactly as they wrote it, word for word with its spaces and no hyphen added ("pinkish red", not pinkish-red). Make no call, change no setting, and do not say that nothing needed changing.'
OWN_SETTING_ASKED_NOTE = "About this request: it asks which value the user's own Ditto appearance preference holds for one setting (accent colour, interface font or colour mode). Their note may not name the setting: keeping their own interface in a typeface gives the font, what their Ditto appearance follows (light, dark or system) gives the colour mode, and a colour they like for Ditto itself gives the accent. Answer with that note's value in double quotation marks exactly as the note writes it, with no hyphen added; a value they turned down or a client's brand value is not theirs. Make no call."
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
    "option_lookup": OPTION_LOOKUP_NOTE,
    "own_setting_stated": OWN_SETTING_STATED_NOTE,
    "own_setting_asked": OWN_SETTING_ASKED_NOTE,
}


def add_on_note(names: list[str]) -> str:
    return ("About this request: it names the listed add-on tool " + " / ".join(names) + ". Call it right away, passing the subject the message names; fill any required field the message leaves out with a usual value (a timer runs 25 minutes) instead of asking, "
            "and do not look up or ask for figures, phrases or links first. Its result may not label the figure as the code, id or number you asked for: the figure it states for the subject the message names is that answer, so give it exactly as written, not another figure from its output.")


def guidance(message: str, tool_names: Iterable[str]) -> list[str]:
    names = list(tool_names)
    return [add_on_note(add_on_tools(message, names)) if kind == "add_on" else NOTES[kind] for kind in request_kinds(message, names)]


def guide_block(message: str, tool_names: Iterable[str]) -> str:
    return "\n".join(guidance(message, tool_names))
