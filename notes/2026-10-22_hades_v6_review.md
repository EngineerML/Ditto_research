# Hades v6 review (2026-10-22)

Agent e6638d76, bench 13, sha256 2c42cb08..., released 2026-10-22. Source in
`released/hades-v6_e6638d76/src/` (not committed). Python 3.12, FastAPI, httpx, ~5.9k lines,
one uvicorn worker, SQLite store. Leaderboard: composite 0.804, gate factor 0.967 (blinkrazor 0.936).

## Correction to the improvement plan (step 1)

Swallowed model calls do **not** zero a case in ordinary scored runs. The broker matches
`tool_endpoint` requests against model emissions session-wide, and an emission that is never
executed "is reported run-wide as `model_selected_not_executed` ... and does not by itself zero a
case" (`services/dittobench-api/PROTOCOL.md:352-355`, `inference_broker.go:2216-2255`, where the
per-case `ModelSelectedNotExecuted` is always 0). What zeroes a case is an **unmatched** request:
changed arguments, no model backing, or a replayed emission (409). Case-window paths
(confirmation, legacy) still book emissions per case, so swallowing is not free everywhere.
Step 1 stays useful but is no longer the top item.

## The request path, step by step

1. **Container.** `Dockerfile`: python:3.12-slim pinned by digest, `uvicorn app.main:app`, port 8080.
   All behaviour is set by env flags in `app/config.py` (about 60 switches, all on by default).
2. **`POST /seed`** (`main.py:46`). Upserts pairs, subjects and links in one SQLite transaction
   and bumps a per-user version (`store.py:96`). Then embeds new records through `/api/embed`
   (`embeddinggemma`, the validator maps it). An embedding failure is logged and the reply is
   still 200, so a wave is never lost (fixes what blinkrazor gets wrong).
3. **`POST /run`** (`agent.py:116`). 285 s case budget. Builds the per-case memory tools, the tool
   executor and a token tally.
4. **Lane choice** (`routing/lane.py:250`, about 400 lines of regex and word lists). Reasons
   such as `imperative`, `imperative-setter`, `read-capability`, `live`, `arithmetic`,
   `names-tool` go to the action lane; `statement`, `question`, `stored-detail`,
   `record-anchor`, `stored-figures` go to the records lane. Typos are folded to cue words with
   one-edit matching.
5. **Lexical retrieval** (`memory/retrieval.py:328`). Each record is indexed by typed values:
   emails, codes, quoted phrases, full names, initials, capitalised words and bigrams. Question
   anchors are weighted by type and rarity; there is a conjunction bonus, IDF coverage seeds and
   up to 3 hops of score propagation along shared values. The output is a pinned/confident set
   plus a tail.
6. **Lane rescue** (`agent.py:134-139`). An action-lane request goes back to records when it
   carries an identifier that 3+ records share, or it is a question about the user's own
   records, or a `live` cue ("latest", "current") is about things held in the records.
   This is their fix for the O_mem leak.
7. **Records lane, three paths:**
   - **Program short path** (`short.py:177`): an identifier held by 3+ short records. Statements
     are grouped, one LLM "order pass" ranks them by writing order, then a "shared draft" is
     written once per (user, notes, asked sentence), and a deciding call answers. Both the order
     reading and the draft are cached across cases, so rewordings of one question get the same
     reading and draft. This is aimed straight at the twin and M_meta gates.
   - **Topic path** (`short.py:358`): a dense topic (3+ multi-paragraph notes). Passages naming
     the phrase, plus a code-picked "most recent passage", plus a "latest passages" draft,
     then decide.
   - **Full records engine** (`records.py:414`):
     a. Recall turn (low effort, memory tools offered). Memory reads are **sent to
        `tool_endpoint`** (to consume the emission) and answered from the local store; the hits
        are pinned into the packet.
     b. Packet (`packet.py:199`): thread-first grouping by shared codes, value closure, link hop,
        dense additions (5 records, 6k chars) and an RRF fusion of lexical and dense order.
     c. Helpers placed before the record context: a coverage block (which stored conversations
        contain each distinctive term) and a figure worksheet.
     d. One of: a timeline pass; or up to 5-6 search passes with a local `find_in_records` tool
        (temperature 0.7, distinct seeds); or a reading pass over the closest records.
     e. Decide (temperature 0, seed 42). Then deliberation: 2 more drafts at temperature 0.7 with
        `tool_choice none`, and a final reply that sees all 3. Then a follow-up-question pass
        and a rewrite that may add it.
8. **Action lane** (`action.py:240`):
   - Tools are reordered for presentation (route by catalog + word match), never removed.
   - **Plan-first** (`action.py:216`): one extra call with no tools asks "which tool should your
     first call use, or NONE". The answer stays in the conversation; the host does not parse it.
   - Up to 8 turns. Unknown tool, missing required argument, wrong JSON type and unreadable
     arguments are answered locally with a "not sent" note (model gets to fix it). Memory reads
     are answered locally and **not** sent.
   - The executor sends the model's **raw argument string** verbatim (`executor.py:41-47`), so
     the broker's canonical match cannot drift.
   - An identical repeat goes through a one-word SEND/HOLD model check (`action.py:51-58`); HOLD
     is reported to the model as not sent.
   - A suffix on tool results says "a call whose result is above has already been carried out"
     (fights E_tool), plus a "result read" pass that lists what each call did.
   - Closing turns force a reply when the model went silent.
9. **Executor** (`tooling/executor.py`). Hop counter per call; one retry only on a 429 admission
   refusal; any 4xx = refused, not recorded; transport loss = outcome unknown, and an identical
   later call is blocked. Only acknowledged calls enter `tool_calls`. Memory mutations are sent
   first, then mirrored into the local store.
10. **Reply.** `final_text` is the model's text unchanged; `answer` is the value of the last
    `ANSWER:` line (`answer.py:34`) with only a surrounding `**` pair removed; `abstain` is
    never set.

## Against our plan (written for blinkrazor)

| plan step | Hades v6 |
|---|---|
| 1 execute every emitted call | no: still rejects locally and has SEND/HOLD; per the correction above, cheap anyway |
| 2 no "retry once" hint | yes: no such hint; the result suffix discourages repeats |
| 3 memory questions out of the action lane | partly: regex lanes plus three rescue rules |
| 4 temperature 0, no rewrite | partly: decide at 0 / seed 42; drafts and search passes at 0.7; follow-up rewrite kept |
| 5 acks restate the value | yes: action prompt quotes stated values, statements go to records lane |
| 6 grounded declines | yes: names who/what was checked, never labels or figures (canary-safe) |
| 7 `/seed` never fails after commit | yes |
| 8 dense always added | no: dense additions only when the question is anchored (`packet.py:202`); unanchored keeps 3 lexical records |
| 9 cost | worse: recall + up to 6 search passes + reading + 3 drafts + decide + follow-up + rewrite; action lane adds plan + result read |

Still open in Hades: two answer separators (" and " in `records.py:36`, " ; " in `short.py:28`).

## Risks before reusing it

- Cross-case caches (order reading, shared draft) are keyed by content, not case id, and are
  declared in `DECLARATION.md`. They work for consistency, but they are the kind of state
  shortcut the rules watch. Keep the declaration if we keep them.
- Local helper tools (`calculate`, `find_in_records`) are added to the deciding catalog. Their
  calls are model emissions that are never sent, so they raise the run-wide
  `model_selected_not_executed` count.
- `lane.py` is fragile word-list routing; any change needs same-seed A/B runs.

## Verdict

A better base than blinkrazor: higher gate factor, smaller code, and steps 2, 5, 6 and 7 are
already done. The work left is steps 4 and 8 (consistency, dense retrieval for unanchored
questions), one answer separator, and cutting passes to lower cost.
