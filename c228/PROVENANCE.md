# Provenance

## Base
This harness is the publicly released crown-v228 v1 (agent `673386d0-cc54-4acc-986c-f0d2663615ec`, archive sha256
`212288958f1c0504cf49b30008c161ced7b6c22a7b3b1d4df27e0982b66d9ee6`, bench 18), released by the subnet on 2026-11-14
03:08 UTC. Building on a released agent is permitted. `DECLARATION.md` is crown-v228's own declaration, kept as
shipped, with our changes listed in a section at its top. crown-v228 is itself built on the released dan0l v30 and
Hades v26 sources (its declaration, §0).

Some changes below come from our own earlier agent, overhorizoner v3 (agent `c88411ed`, built on the released dan0l
v42), which is our code.

## Changes from crown-v228

`app/evidence.py` (the tied-names view) is crown-v228's own, except that the list note below joins its notes and the asked-name row below filters its ties.

| Change | Files |
|---|---|
| Polling: an identical status read goes out again, with no repeat check, while its last result says the job is running, pending, queued or retrying. From overhorizoner v3. | `app/tools.py` |
| Already-tracked hold: when the message asks for a new item only if none exists, and a listing from the same app already holds an item naming the current identifier another source gave, the first create call to that app is not sent and the model is told which item holds it; it may send the call again. If its reply then leaves that item's reference out, it is asked once to write the reply again. From overhorizoner v3. | `app/tracked.py` (from overhorizoner v3), `app/action.py` |
| List before create: the same kind of message, when the first create call to the app it names comes before any listing of that app was read, is not sent; the model is told to list first, and may send it again. | `app/tracked.py` (`unlisted_create`), `app/action.py` |
| Finished run first: when the message waits for a run to finish and the latest job listing still shows the run or its retry as running, the first call that would post or send something is not sent; the model is told to read the job listing again. It may send it again. | `app/jobs.py` (new), `app/action.py` |
| Program notes: a message asking whether the records agree on who did something gets a note to name every person a record credits, then "agree" or "disagree" (no record replaces another here); a message asking what was settled on for something gets a note to give only the action that stands, ending where the action ends. | `app/guide_records.py` (`plan_notes`, `RECORDS_AGREE_NOTE`, `PLAN_NOTE`) |
| Open the page: for incident-triage and pricing-correction requests a lone web search gets the open-the-page note, never the reply-now note. | `app/action.py` (`PAGE_KINDS`) |
| Spend governor: the tokens of each finished request, priced at the bench's published chat rates, go into a window of the last 100 requests. While the window averages over $0.0035 per request (about 1.6 times the costliest stretch of an ordinary run), later calls go out at low effort with at most 4,000 output tokens, and over $0.0050 with at most 1,500; under $0.0028 they go out as before. It reads only that window, so process age and the number of runs served never matter. It changes no message or tool. | `app/governor.py` (new), `app/llm.py`, `app/agent.py` |
| Tool names: anything after the first character that cannot be in a tool name ("read_links?commentary?json") is trimmed, as the `<|` marker already was. | `app/llm.py` |
| List note: a message that asks for two, three, four or both things, or every one, gets a note to answer with the ones the notes give and say nothing about the rest; only when the notes give none of them does the reply say there is no record. The tied-names view drops its "not stated" line when this note is on. | `app/guide_records.py` (`LIST_ASK_RE`, `LIST_PARTIAL_NOTE`, `list_partial_notes`), `app/evidence.py`, `app/action.py` |
| Called names in long records: the called-name search (crown's M48) also reads a long record, but only its sentences that write the full name the message uses, and also takes a name quoted a few words after the cue ("who nobody has called anything but \"Pip\""). When no short record holds that name, the long ones that do are listed. | `app/memory/coverage.py` (`QUOTED_CALLED_RE`, `called_in`, `called_names`) |
| Number threads: when the message writes a full name and a packet record writing it holds a five-plus digit number, stored records holding that number (a number held by 2 to 12 records) are seated right after that record oldest first, and the numbers they hold are followed the same way, up to 5 hops and 24 records in all. Records are moved or added, never edited. From the released dan0l v59 (agent `a06c97e5`), `app/packet.py` `number_threads`, unchanged except that crown's packet has no merged copies. | `app/packet.py` (`NUMBER_RE`, `asked_full_names`, `number_holders`, `number_thread`, `number_threads`), `app/records.py` |
| Referring turns: after a packet record that writes the asked full name, the very next turn of the same conversation (same session id), whatever the time between them, when it names nobody and speaks of someone by a phrase ("The person I shared the taxi with ...", "The person from the post office queue ...", "My quiz partner ..."), is added or moved right after that record, up to 6. Its entry carries `sameConversationAs` and `phraseMeans` (the asked name), and a note before the message names each such mark and the record it follows. crown's own follow-up turns stop at 20 minutes, so a turn 41 minutes later was never seated. Our own code. | `app/packet.py` (`REFERS_BACK_RE`, `referring_turns`, `memory_entry`), `app/records.py` (`REFERS_BACK_NOTE`, `REFERS_BACK_LINE`) |
| Asked name in the tied-names view: a capitalised word the message writes in one run with the asked full name ("Xocelo Junhaorl Granary") is part of the asked name, so it is never taken as another name of that person. Before, such a word made the view show only the notes writing it and answer from them. | `app/evidence.py` (`tied_names_view`) |

None of these makes a model call. Every hold releases the call when the model sends it again.
