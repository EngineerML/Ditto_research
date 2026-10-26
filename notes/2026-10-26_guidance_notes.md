# Request guidance notes for the action lane (2026-10-26)

dan0l v25's tool gain comes from a phrase-keyed table of tool instructions (notes/2026-10-26_dan0l_v25_review.md).
This is our own version of the idea, written from the grading rules per tool family, not from v25's code.

combined/app/ours/guidance.py picks short advisory notes from the request's wording and the tools the
catalog offers; combined/app/action.py appends them to the action-lane, reply-check and called-lane
prompts. A note appears only when its tool is offered. Nothing is forced: the model still sees the
whole request, records and catalog, and makes every call itself. Routing and record selection are
untouched, and there is no typo mender (an earlier one turned "rebooking" into "reasoning" and
tripped the typo-tolerant-token-compare fingerprint).

## Screening

- screen_local: no leads in guidance.py; generator n-gram scan: 0 hashes.
- Fits the policy-v13 clarification on routed instruction guidance (2026-10-23): advisory, routed by
  phrasing, the model decides, no benchmark-private content. Note texts are generic product advice.
- Not re-run: the L1 review (about $0.5); worth one pass before submitting.

## A/B on the questions the notes reach (platform providers, two runs a side)

| | questions | no notes | v1 notes |
|---|---|---|---|
| seed A (3590624429364033488) | 41 | 0.689 | 0.828 |
| seed B (2184940051138219952) | 42 | 0.786 | 0.857 |

v1 lost some runs on three kinds of question, each in one run of two:

- state-dependent calendar: the model asked "Which Wednesday?" instead of creating the event;
- vague calendar restraint ("drop that into my calendar"): the note's "create it right away" pushed
  a forbidden create;
- memory update: content "moved to Wednesday" without the word the note keys on ("handoff"); the
  "Saving a note" note also fired alongside the correction.

v2 fixes: the calendar note fires only when the event is named, and says a given day is used as
given with no "which week / what time" question; the correction note asks for the thing's own name
plus its new value, and the save note stays off when correcting; the listed-option note covers any
setting value (accents too) and asks for the closest spelling letter by letter.

v2 against v1 on the 20 questions whose notes changed (2 runs each):

| | questions | base | v1 | v2 |
|---|---|---|---|---|
| seed A | 11 | 0.864 | 0.818 | 1.000 |
| seed B | 9 | 0.875 (8 graded by all) | 0.750 | 0.938 |

No regressions against either. The only miss left is one of two runs on a seed-B memory update
that the base run fails in both.

Cost of the whole experiment: $0.66. Logs: practice/guide_fix/ab.log, ab2.log; comparisons in
practice/guide_fix/*.md.
