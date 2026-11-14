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

| Change | Files |
|---|---|
| Polling: an identical status read goes out again, with no repeat check, while its last result says the job is running, pending, queued or retrying. From overhorizoner v3. | `app/tools.py` |
| Tied-names view, initials: initials a short note gives the person with a called-name cue ("has gone by S.B.", "knows X as V.H.", "when the gang says K.D. they mean X") tie to them like a nickname; "gone by", "went by", "knows … as" and "they mean" join the called-name cues. | `app/evidence.py` (`initials_ties`, `name_pattern`, `CALLED_CUE_RE`) |
| Tied-names view, list answers: every item found goes on the answer line, and nothing is written about items not found; the "say what is not stated" line is left out of this view only. Any liking or frequenting verb in a note counts as the asked one. The view keeps up to 28 notes instead of 14, so short chatter about a person no longer stops it. | `app/evidence.py` (`TIED_NOTE`, `EvidenceView.list_ask`, `answer_from_view`, `TIED_MAX_NOTES`) |
| Tied-names view, code-read list: beside the notes, code lists the place or thing each note names when the person, under one of their names, is its subject (not a possessive such as "X's sibling", not a note in the past tense, not a note about work). It is shown only when it holds exactly the number of things asked, none twice, and is headed as found by code and not checked, the notes deciding. No model call. | `app/evidence.py` (`things_named`, `TIED_READ`) |
| Already-tracked hold: when the message asks for a new item only if none exists, and a listing from the same app already holds an item naming the current identifier another source gave, the first create call to that app is not sent and the model is told which item holds it; it may send the call again. If its reply then leaves that item's reference out, it is asked once to write the reply again. From overhorizoner v3. | `app/tracked.py` (from overhorizoner v3), `app/action.py` |
| List before create: the same kind of message, when the first create call to the app it names comes before any listing of that app was read, is not sent; the model is told to list first, and may send it again. | `app/tracked.py` (`unlisted_create`), `app/action.py` |
| Finished run first: when the message waits for a run to finish and the latest job listing still shows the run or its retry as running, the first call that would post or send something is not sent; the model is told to read the job listing again. It may send it again. | `app/jobs.py` (new), `app/action.py` |
| Program notes: a message asking whether the records agree on who did something gets a note to name every person a record credits, then "agree" or "disagree" (no record replaces another here); a message asking what was settled on for something gets a note to give only the action that stands, ending where the action ends. | `app/guide_records.py` (`plan_notes`, `RECORDS_AGREE_NOTE`, `PLAN_NOTE`) |
| Open the page: for incident-triage and pricing-correction requests a lone web search gets the open-the-page note, never the reply-now note. | `app/action.py` (`PAGE_KINDS`) |
| Spend governor: the tokens of each finished request, priced at the bench's published chat rates, go into a window of the last 100 requests. When the window's average passes $0.0020 per request (on pace for about $0.70 a run), later calls go out at low effort with at most 4,000 output tokens, and past $0.0028 with at most 1,500; under $0.0016 they go out as before. It changes no message or tool. | `app/governor.py` (new), `app/llm.py`, `app/agent.py` |
| Tool names: anything after the first character that cannot be in a tool name ("read_links?commentary?json") is trimmed, as the `<|` marker already was. | `app/llm.py` |

None of these makes a model call. Every hold releases the call when the model sends it again.
