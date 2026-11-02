# 2026-11-02 — v8 against DrPresident v22 (released 2026-11-01)

DrPresident v22 (agent eeb26552) is the best released agent we hold: mean 0.9462 over 18 samples, against
0.9347 for dan0l v30, our base. Its source is in `released/DrPresident-v22_eeb26552`. No model calls were made
for this comparison.

## Same seeds, program questions

DrPresident's three public runs are on three of our s44 seeds, so the comparison is like for like. Its
`case_results` carry no case ids, so program totals are summed over the program categories (`v13-open-program`,
`v13-personal-program`). Its splits come from the consistency factor (13 groups, enterprise included).

| seed | DrPresident v22 (public run) | v8 real s44 round | v8 replays A, B, v81 |
|---|---|---|---|
| ..471344 | 40.0/40, 0 splits | 40.0, 0 | 39.5, 38.5, 40.0 |
| ..320626 | 38.0/40, 1 split | 38.5, 0 | 38.0, 38.5, 38.5 |
| ..906855 | 33.5/40, 0 splits | 32.0, 0 | 36.5, 34.0, 37.0 |
| mean | 37.17, 1 split in 3 runs | 36.83, 0 in 3 | 37.6 (replays omit tools and the final check) |

- On these seeds the program questions are a tie within noise.
- v8's case for itself is splits: 0 in every sample on its path, where DrPresident had 1 in 3 runs.
- Both find seed ..906855 hard.
- Enterprise questions: DrPresident 36/36 over its three runs; v8 35/36 over the three s45 seeds.
- DrPresident's other memory means on these seeds were 0.953, 0.932 and 0.920, with tool means 0.997, 0.990 and
  0.970. We have no full v8 run on them.

## How the program paths differ

| | DrPresident v22 | v8 / v8.1 |
|---|---|---|
| Separate reading of the notes | "state reading" (one call, notes only, no message): one line per tracked item with its value now and the marks it rests on; shared by user + system + notes since v21 | "ledger" (one call, notes only): defined labels, each change `before -> after`, DATED lines, NOW lines; shared by user + system + notes |
| How it reaches the deciding call | inside the user turn, under "as a separate reading of the notes alone wrote it before the message was read (not checked; the notes decide wherever they differ)" | as an assistant turn, then REPLY_NOTE "from the ledger, which already applies every entry: take what it holds" (**rejected under I4**) |
| Reading rules | in the deciding system prompt: SYNONYM, CORRECTION, EVENT_DATE, ONE_VALUE (with client vs vendor), LIST, AFTER, FORM, STEP; plus a fixed host PROGRAM_NOTE on revert and strike | READING_RULES in the ledger call's system prompt (order, labels, separate matters, item identity, changes, going back, lists, plans, roles and money direction, dates, people, values); ANSWER_RULES in the deciding prompt |
| Rewordings | EARLIER_REPLY_NOTE in the user turn: "An earlier reply to the question …: … When the message below asks the same thing in other words, give the same value as that earlier reply." Keyed on user, system, notes shown and the asked sentence's answer form. Its declaration cites the 2026-10-29 I4 clarification on reused replies, and it passed screening. | earlier question and reply as assistant turns, REWORDED_NOTE "with the same value in the same words as the reply above"; keyed on the asked part |
| Notes shown | filing order, same-minute copies once, a lead of statements in filing order | filing order, same-minute copies once (`once_each`) |
| Case-file questions with words like "news" | `own_records_question(held)` since v19 | the same fix in v8.1 |

**Reading.**
- The two designs converge: a notes-only reading, shared across rewordings, then a deciding call.
- The only difference that matters for screening is the framing. DrPresident's reading is labelled advisory
  ("not checked; the notes decide"), and that passed. Ours was framed as settled, and that failed.
- In our replay, advisory framing of the ledger cost about 2 questions per seed (v8.2). DrPresident gets level
  scores with advisory framing. Its reading rules sit in the deciding prompt, so the deciding model re-reads the
  notes under the same rules the reading used.
- Our ledger keeps its rules in the reading call only, so a reply told to re-read gets no rules. That is a likely
  reason v8.2 lost.

## What v8 has that DrPresident v22 lacks

- READING_RULES items DrPresident does not state:
  - item identity (one slot worded two ways);
  - going back after A, B, C gives B (DrPresident has this in PROGRAM_NOTE);
  - separate matters;
  - labels read by their defined meaning;
  - money direction (DrPresident has client vs vendor in ONE_VALUE_RULE);
  - an action without its timing.
- An explicit change log (`before -> after`) in the reading, not only the value now.
- Zero splits on the program path across 230 sampled groups.

## Next

DrPresident v23 is released 2026-11-02 18:41 UTC. Plan: read its diff against v22. Then choose between two
routes, both advisory under I4:
- port our reading content into DrPresident's state reading;
- give our ledger DrPresident's framing and put the reading rules in the deciding prompt.

Compare both with the reply-only replay on the same ledgers.
