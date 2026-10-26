# Topic path fix: thread state, spelling, contact cards (combined, 2026-10-26)

## Why

The loss sort of the combined full run (tools/loss_causes.py) put most lost memory points in
"all evidence seen, answer wrong", and 14 of those on the topic path (world-story threads):
contact questions answered with the employer and city or the earlier holder's email, status
questions answered with the next step, and misspelt words copied into the answer ("switched
ovir", "delivery dage") so the answer no longer read as the right state or action.

## Change (combined/app/short.py, topic path only)

- THREAD_STATE in the topic system prompt: asked where a thread stands, give its state after
  the latest change, not the next step; asked what happens next, give the next step.
- TOPIC_SPELLING beside the unchanged VALUE_VERBATIM: ordinary words keep their usual
  spelling; names, codes, email addresses and handles stay as written.
- Contact questions: the cards of everyone the thread names are added after the reading's
  pick (same character budget), and an advisory CONTACT_NOTE asks for the person's own contact
  detail, not the employer or a team or thread inbox.

Only the 77 questions whose prompts used the topic-path system texts can change; every other
question's prompts stay byte-identical.

## Rules

Records are only added (I2/W3); no answer, slot or abstain is rewritten and no derived value is
shown (I3/I4); the tool catalog is untouched (I7); the guidance is general advice routed by
the request's wording, which the 2026-10-23 "routed instruction guidance" clarification allows,
with no benchmark vocabulary, no private knowledge and no generator wording (I5).

## A/B on the 77 questions (subset scorer, every wave seeded, writes replayed)

| | old (3 runs) | v1 (2 runs) | v2 (2 runs, kept) |
|---|---|---|---|
| mean score | 0.775 | 0.838 | 0.857 |
| regressions (passed every old run, failed a new one) | | 2 | 1 |
| gains (failed every old run, passed a new one) | | 6 | 7 |
| model calls / question | 3.45 | 3.27 | 3.26 |

- v1 wrote "copy ... numbers exactly as written": the model then copied a written cap instead
  of working out the remainder (0/2), and "whoever holds the thread" pulled a thread inbox once.
  v2 keeps VALUE_VERBATIM as it was and names the person's own contact detail; both questions
  pass 2/2.
- v2's one regression (status question, 1/2) parts at the first call of the two v2 runs
  (sampling) and the failing run answered the next step: the kind of slip THREAD_STATE is for,
  not one it causes.

Expected effect on a full run: about +6 memory points of 250, memory mean +0.025, composite
about +0.013. Reports: practice/topic_fix/ab_v1.md, ab_v2.md.
