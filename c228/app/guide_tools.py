from __future__ import annotations

import re
from collections.abc import Iterable

from .connectors import APP_READ_TOOL, APP_WRITE_TOOL, TOOL_APP, named_apps
from .request_kinds import add_on_tools, request_kinds

WORKFLOW_FOLLOW_NOTE = "About this request: it asks to run a saved workflow, wait for its run to finish, post the figure that run reports in the app it names, and report that figure. Call list_workflows first and run the active workflow that bears the name given, with run_workflow and its id as listed; an archived or old version of it is not it. The run comes back as a job: call list_agent_jobs and read that job's line, and while it says running or in progress, call list_agent_jobs again; when it says the job failed and was retried under another job id, that retry is the run to follow. The figure is the one the completed job of this run reports, not the figure of last week's job. Then post that figure in the app with the app's own creating or posting tool, the figure itself in the title or text you post, even where that tool's description names another kind of item; a reply without that call has not posted it. Reply with that figure alone, written as the job reports it."
INCIDENT_TRIAGE_NOTE = "About this request: it asks for the vendor's current incident in the user's region from the vendor's status page, a check of the app it names for an existing item on it, and a filing only when there is none. Search the web for the vendor's status page (search_web with the vendor's name), open the status page itself with read_links, and take the incident whose line names the user's region; an incident for another region, and one listed as resolved, is not it. Then call the app's listing or search tool to look for an existing item naming that incident id; a reply that nothing matched from one of the app's tools is not that check, so call the app's other listing tool then. When an item names it, file nothing, and the reply gives the incident id and that existing item's reference code copied from the listing (for example: Incident ID: <id>; already tracked as <ref> in <app>); only when none names it, create one item in that app with the incident id first in its title. Reply with the incident id and what you did, and never create before the listing call has been made and read."
PRICING_CORRECTION_NOTE = "About this request: it asks for the current per-seat price of one plan from the vendor's own pricing page, with any correction to that plan applied, and the yearly total for the seats given. Search the web for the vendor (search_web with its name), open its pricing page with read_links, and read the plan's listed price. When the page points to a correction or notice, open that link with read_links too: the correction applies only when it names this plan, and a notice page that says it was itself superseded or is out of date, or that names a later notice or a current one, is not the end: open that later notice with read_links before working anything out, since its figure is the one in force. A forum thread is not the pricing page. Work the yearly total out with run_code, 12 x seats x the price in force, and reply with the per-seat price in force and that yearly total, giving no other total."
RECONCILE_RECORDS_NOTE = "About this request: two apps hold different values for the same renewal; it asks which value is current and who approved it, and nothing is to be changed. Read the record in each of the two apps with that app's listing or search tool, the renewal's name as the filter; a reply that nothing matched from one of the app's tools is not the record, so call the app's other listing tool then, and the web and the user's notes are not those apps. The value in force is the one most recently approved or signed off; a revision that is proposed, a draft, or awaiting approval is not in force whatever its date, so the earlier approved value stands then. Reply with that value and the name of the person who approved it, giving no other figure, and make no write."
BILLING_HANDOFF_NOTE = "About this request: it asks for the amount a client owes, read from the app it names, emailed to the client's billing contact with the invoice number, and reported back. Read the client's record with that app's listing or search tool, the client's name as the filter; a reply that nothing matched from one of the app's tools is not the record, so call the app's other listing tool then. The amount due is the balance due after any credit applied. The billing contact is the one the user's latest note names as current: when a note says the contact changed, the new one and never the former. Send one email with gmail_send to that contact's address with the amount due and the invoice number in it, then reply with the amount due and the contact you emailed."
SETTING_CHECK_NOTE = "About this request: it asks you to make sure one of the user's Ditto appearance settings (accent colour, chat font or colour mode) has a certain value. First find the user's note that keeps their own value for that same setting. The values are the same only when every word matches: a name with a word added or dropped (Martel and Martel Sans, plum and plum purple, grey and storm grey) is a different value. If that note already keeps the value the message names, nothing needs changing: make no call at all, not even a lookup, and reply that it is already set to that value, naming the value as the note writes it. If the note keeps a different value for that setting, call the setter for that setting with the value the message names; a reply that says it is set to the other value, without the call, is not the answer then."
SCHEDULE_NOTE = "About this request: it asks about the user's workflows that run by themselves at set times (recurring, timed or repeating). When each one runs and how many runs it has logged is what list_schedules returns: call list_schedules for it (list_workflows lists the saved workflows themselves, not their schedule), and answer from its result."
SAVED_WORKFLOW_NOTE = "About this request: to run a workflow the user has already saved, first call list_workflows to find it by the name or schedule the message gives, then call run_workflow with its name exactly as listed."
AGREED_NOTE = "About this request: it asks to start work the user says was agreed earlier. Find the user's decision note about this project's work; its own words say which one thing to do, and you do that and nothing else. If it says to create a new reusable workflow, call create_workflow once under the name the note gives; list nothing first and run nothing. If it says to run an existing workflow, call list_workflows, then run_workflow with the workflow name exactly as the decision note writes it; when the list does not show that workflow, its id is unknown, so pass that name in run_workflow's name field; another workflow in the list is a different one. If it says to dispatch a one-off background job, call execute_agent_job once."
REPEATING_NOTE = 'About this request: it asks for something to happen on a repeating schedule: create it now with create_workflow, with the schedule and the action the message states; fill anything it leaves open with a usual choice instead of asking.'
CAPABILITY_NOTE = 'About this request: it asks what Ditto can do or how to do something in it. Look it up with discover_capabilities first and answer from what it returns; it asks how, not for the change itself, so change no setting.'
EARLIER_IMAGE_NOTE = "About this request: it asks to change an image made earlier in this chat. If neither the message nor the notes give a link for it, call edit_image right away with image_url set to the image as the user refers to it (for example 'the last image you made') and the change as the instruction, instead of asking for a link."
CALENDAR_NOTE = "About this request: it asks to put an event on the calendar. Read the user's notes about this event first. If a note says it is already on the calendar, find it with calendar_search_events and say where it is; do not add another. If a note says its date has not been decided yet, ask the user when, naming the event, and add nothing. In every other case, including when no day or time is given, create it right away with calendar_create_event: the title is the event's name as the message or the note gives it (never a reference code), and 'when' is the day or time the message or the note gives, or 'unscheduled' when neither gives one, since the user can move it later; do not ask when."
CALENDAR_LOOKUP_NOTE = "About this request: it asks whether, or when, something is on the user's calendar. Call calendar_search_events once, with the event's own words as the query, and answer from what it returns; the user's notes are not the calendar, and the workflow schedules are not the calendar."
FEEDBACK_NOTE = "About this request: it is feedback meant for the Ditto team: file it with file_feedback_for_team, its text in the user's words. It is not an email to anyone."
REASONING_NOTE = "About this request: it is about how much reasoning the user wants by default. When it states the level (deep or careful thinking is high, balanced or moderate is medium, quick or minimal is low), set it now with set_reasoning_effort. When it asks for the way they usually like it, set it now with set_reasoning_effort to the default their note names; if their note says they have not picked one yet, set nothing and ask which reasoning effort level they want as their default, naming each option in the note's own words, copied as the note writes them, not as low, medium or high."
TASK_NOW_NOTE = "About this request: it asks for a task to be carried out now rather than explained: start it with execute_agent_job, the task in the user's words. That background job does the whole task itself (code, scripts, scraping, reports, apps), so the task goes to it even when a web search, a picture, an artifact or a script written into your reply could cover part of it; do not ask for files or links first."
SANDBOX_NOTE = 'About this request: Run it with run_code: a short snippet that calls the routine by the name the user gives, and report exactly what it prints. It is not a background job.'
ARITHMETIC_NOTE = 'About this request: it asks for arithmetic over figures it states: compute it with run_code (a short snippet) and report the result, even when the user says no script or project is needed; that only rules out building something bigger.'
SEARCH_THEN_READ_NOTE = "About this request: search with search_web, then open the top result's link with read_links and answer from that page. A search result shows only a short preview of each page, and the preview is not the page: open the top link with read_links before you answer, even when the preview already seems to answer, and give the figures the page itself states."
ARTIFACT_NOTE = 'About this request: it asks for something the user can open and use: build it with the artifacts tool, not as an image.'
TOOL_LOOKUP_NOTE = 'About this request: Look through the available tools with search_tools first and answer from what it finds, naming the tool; it asks which tool fits, so leave the tool it finds unused.'
COLOUR_MODE_NOTE = "About this request: it asks to set Ditto's colour mode now: call set_theme with dark or light as asked, or system when the app should follow the device, even if a note mentions another mode; the request is the current instruction."
HANDOFF_NOTE = 'About this request: it corrects a fact in a note the user saved earlier: the handoff scratchpad of the project the message names, the note that calls itself that project\'s handoff scratchpad, not the project\'s own records. If that note is not among the records shown, find it with search_memories first. Call update_memory on that note\'s pair_id with short content that names the project and states only the corrected fact, for example: handoff for the "<project>" scratchpad is Wednesday; add the reviewer only when the message itself names one. Do not rewrite the whole note or save a new one.'
DISPOSABLE_NOTE = 'About this request: it asks to delete one disposable note about a person (an email-fix receipt or scratch note) while keeping their contact record. The note to delete is the receipt or scratch note itself, the one that calls itself a receipt or scratch note and says it can be deleted; a record saying they moved and giving their new work email is part of their contact history and stays. If that note is not among the records shown, find it with search_memories first. Then delete only it with delete_memory, using its pair_id; their contact, work and email records stay.'
SEND_TO_THEM_NOTE = "About this request: it asks to send numbers or an update to 'them', and asking for it now means it is ready to go. The user's note on this project says who gets it: the person who asked for it, if someone asked; otherwise the recipient the note plans for. Send it right away with gmail_send to that person's address; the body simply says the figures or the update are ready; do not ask the user for the numbers. Only if the note says the user has not yet decided who gets it, ask which of them gets it, naming each person the note names, and send nothing."
LIVE_FIGURE_NOTE = 'About this request: Look the figure up live with search_web first (a figure the notes give is not a live one), then email what you found with gmail_send to that person, at the address their record gives.'
KEEP_THIS_NOTE = 'About this request: Save it with save_memory, then confirm what you saved, repeating the value in double quotation marks exactly as the user wrote it.'
TOOL_PREFS_NOTE = "About this request: it sets which tools are used in the user's chats from now on. Call set_chat_tool_preferences right away with the preference in the user's words; that call itself keeps it as their default, so it needs nothing before it: no saved note and no tool search."
WORKFLOW_BUILD_NOTE = "About this request: it asks for a reusable workflow built from the goal it names: create it now with create_workflow, the goal in the user's words and its parts as steps, and fill anything it leaves open with a usual choice instead of asking. One create_workflow call makes the whole workflow."
WORKFLOW_NAMED_NOTE = "About this request: it asks for a new reusable workflow under the name it gives: create it now with one create_workflow call, named as the message writes it, with steps that suit the name. It does not ask whether one already exists, so list nothing first and ask nothing."


MAKE_THEN_EDIT_NOTE = "About this request: it asks for a new image and then a change to it. Create it with create_image first, then call edit_image on the image that call returns, with the change as the instruction."
OPTION_LOOKUP_NOTE = "About this request: it asks to set an appearance option whose name the user may have misspelled. List the options with discover_capabilities first, then call the setter with the listed option that is closest to what they wrote, and say which option you used. When the message asks for a shade, variant, cut, edition or version of a name (the blue shade of that name, its sans cut), the option is the listed name made of that name followed by that word, not the plain name. The listing is the check they asked for, and the setter call follows it in the same request: a reply that says the option was applied without that call is wrong."
WORKFLOW_IF_MISSING_NOTE = "About this request: list the saved workflows with list_workflows first. If none is for this project, create one with create_workflow named with the formal project name the user's records give, and put the reviewer's current email address, taken from their latest contact record, into the review step rather than only their name. Their current email address is the one in the most recent record about how to reach them (after a move or a new job, the new one), and the review step gets that email address itself. If that record is not among the records shown, find it with search_memories first. A decision note about a different project does not apply to this one. A note about a person whose name or nickname differs by a letter (Dani and Danni) is about someone else."
LIVE_WORLD_NOTE = "About this request: it asks what is true in the world now. Look it up live with search_web and answer from what it returns; the user's notes only show what they knew when they wrote them, and setting those notes aside is not a request to delete them."
BACKGROUND_JOB_NOTE = "About this request: it asks for a one-off task to run in the background while the user carries on: start it now with execute_agent_job, the task in the user's words; the job itself works with what the task names, so do not ask for files or links first."
JOB_STATUS_NOTE = "About this request: it asks how background jobs the user already started are doing: check them with list_agent_jobs and answer from what it returns, without starting anything new."
WEB_LOOKUP_NOTE = "About this request: it asks you to look up something the web can answer: call search_web for it and answer from what it returns."
OWN_SETTING_STATED_NOTE = 'About this request: the user is telling you their own Ditto appearance preference. Acknowledge it in one short sentence in your own words that gives only the value itself in double quotation marks, spelled as they wrote it, with its spaces and no hyphen added ("storm grey", not storm-grey); do not quote or repeat their sentence. Make no call, change no setting, and do not say that nothing needed changing.'
OWN_SETTING_ASKED_NOTE = "About this request: it asks which value the user's own Ditto appearance preference holds for one setting (accent colour, interface font or colour mode). Their note may not name the setting: keeping their own interface in a typeface gives the font, what their Ditto appearance follows (light, dark or system) gives the colour mode, and a colour they like for Ditto itself gives the accent. Answer with that note's value in double quotation marks exactly as the note writes it, with no hyphen added; a value they turned down or a client's brand value is not theirs. Make no call."
APP_AS_CONTEXT_NOTE = "About this request: the calendar event or the email is what it asks for. The app it names is only where the work or the details live: make no call in that app, and nothing beyond what it asks for."
WEB_ABOUT_APP_NOTE = "About this request: it asks for a web search, and the app it names is the subject of that search. Call search_web once; make no call in that app."
APP_LOOKUP_NOTE = "About this request: it asks to look something up in the app it names. Call that app's own tool for it once ({tools}), passing the subject the message names, and report the figure it returns; if it answers that the app is not connected, say so. A web search and the user's notes are not that app."
NOTES = {
    "workflow_follow": WORKFLOW_FOLLOW_NOTE,
    "incident_triage": INCIDENT_TRIAGE_NOTE,
    "pricing_correction": PRICING_CORRECTION_NOTE,
    "reconcile_records": RECONCILE_RECORDS_NOTE,
    "billing_handoff": BILLING_HANDOFF_NOTE,
    "app_as_context": APP_AS_CONTEXT_NOTE,
    "web_about_app": WEB_ABOUT_APP_NOTE,
    "setting_check": SETTING_CHECK_NOTE,
    "handoff_correction": HANDOFF_NOTE,
    "disposable_note": DISPOSABLE_NOTE,
    "keep_this": KEEP_THIS_NOTE,
    "tool_prefs": TOOL_PREFS_NOTE,
    "workflow_build": WORKFLOW_BUILD_NOTE,
    "workflow_named": WORKFLOW_NAMED_NOTE,
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
    "make_then_edit": MAKE_THEN_EDIT_NOTE,
    "option_lookup": OPTION_LOOKUP_NOTE,
    "own_setting_stated": OWN_SETTING_STATED_NOTE,
    "own_setting_asked": OWN_SETTING_ASKED_NOTE,
}


SUMMARY_ASK = re.compile(r"\b(?:summar(?:y|ies|i[sz]e[sd]?|i[sz]ing)|digest)\b", re.I)
SUMMARY_SCOPE_NOTE = "The message asks for a summary: keep it to what the output says about the subject the message names; what the output says about anything else stays out of your reply."


def add_on_note(names: list[str], message: str = "") -> str:
    note = ("About this request: it names the listed add-on tool " + " / ".join(names) + ". Call it right away, passing the subject the message names; fill any required field the message leaves out with a usual value (a timer runs 25 minutes) instead of asking, "
            "and do not look up or ask for figures, phrases or links first. Its result may not label the figure as the code, id or number you asked for: the figure it states for the subject the message names is that answer, so give it exactly as written, not another figure from its output.")
    return note + " " + SUMMARY_SCOPE_NOTE if SUMMARY_ASK.search(message) else note




# "Open a Freshdesk ticket ...", "File a new Jira issue ...": the look-up verb opens something new in the app, which is its writing tool.
OPENS_NEW_ITEM = re.compile(r"^\s*(?:please\s+)?(?:open|file|create|log|raise|record|add|post|enter|make|submit|start)\s+(?:a|an|new|another|one|me a|me an|up a|up an)\b", re.I)


def app_lookup_note(message: str, names: list[str]) -> str:
    named = named_apps(message)
    # A lookup in the app is done with its reading tool, and "open a ticket", "file an issue" or "log a call" in it with its writing
    # tool; the app's other catalog tools are neither. The note names that one tool; the catalog is the same.
    chosen = APP_WRITE_TOOL if OPENS_NEW_ITEM.match(message) else APP_READ_TOOL
    tools = [chosen[app] for app in sorted(named) if app in chosen and chosen[app] in names]
    return APP_LOOKUP_NOTE.format(tools=" / ".join(tools or [name for name in names if TOOL_APP.get(name) in named]) or "the one named for the app")


ENCOUNTER_KINDS = frozenset({"workflow_follow", "incident_triage", "pricing_correction", "reconcile_records", "billing_handoff"})
APP_TOOLS_LINE = " The tools of the app the message names, as this catalog lists them: {tools}. Reading, checking or posting in that app is done with these, even where a tool's description names another kind of item: one of its listing or search tools returns the record asked about, and its creating tool posts the item; a web search and the user's notes are not that app. When one of them answers that nothing matched, the record lives under another: call each of the app's other listing tools in turn before concluding that the app holds nothing. A required field the message does not give (a project, repository, board or path) is filled with the subject of the request, such as the client's, vendor's or renewal's name or the incident id, not asked for."


def encounter_note(message: str, names: list[str], kind: str) -> str:
    named = named_apps(message)
    tools = [name for name in names if TOOL_APP.get(name) in named]
    return NOTES[kind] + (APP_TOOLS_LINE.format(tools=" / ".join(tools)) if tools else "")


def guidance(message: str, tool_names: Iterable[str]) -> list[str]:
    names = list(tool_names)
    return [add_on_note(add_on_tools(message, names), message) if kind == "add_on" else app_lookup_note(message, names) if kind == "app_lookup" else encounter_note(message, names, kind) if kind in ENCOUNTER_KINDS else NOTES[kind] for kind in request_kinds(message, names)]


def guide_block(message: str, tool_names: Iterable[str]) -> str:
    return "\n".join(guidance(message, tool_names))
