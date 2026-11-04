# 2026-11-04 — v34 memory ports and the imperative re-route (paid A/B, $1.61)

Builds:
- **v8:** `ditto-harness:drp23v15`.
- **drp23v16:** drp23v15b with fix 1 reverted, plus three dan0l v34 ports (commit 37cfdd6):
  - "answer each thing the message asks";
  - nickname → full name lines and full-name → nickname retrieval anchors;
  - the unnamed-person note.
- **drp23v16r:** drp23v16 plus the imperative re-route (commit 710e399). An imperative reading request with no cue word
  ("Name the two podcasts Pogo keeps recommending"), about names or nicknames the user's records hold, takes the
  records lane.

Balance $9.62 → $8.01.

## Hard pack (`v16_atlas/hardgen`, the c0 shape)

Two-item and three-item lists whose items are stated under a full name, a nickname and initials, with a look-alike
nickname and disliked items as distractors. 2 seeds × 35 cases, policy 16, `tools/generator_panel.py`:

| Family | v8 | drp23v16 | drp23v16r |
|---|---|---|---|
| nickname-list | 0.94 | 0.89 | **1.00** |
| nickname-list-update | 0.66 | 0.69 | **0.94** |
| alias-list-three | 0.76 | 0.78 | **0.80** |
| nickname-list-reverse (asked by nickname) | 0.61 | 0.69 | 0.64 |
| all 70 | 0.745 | 0.765 | **0.842** |

- **Before the re-route, by lane.** Records lane: v8 0.826 against drp23v16 0.859. Action lane, where every "Name
  the …" question went: 0.59 and 0.58.
- In the records lane, cases missing an item fell from 16 to 9.
- The remaining failures are:
  - the follow-up question (M43) naming a distractor ("suggest a bakery other than Maple Crust"), which zeroes the
    case;
  - nickname-only questions missing the item stated under the full name (no nickname → full-name retrieval anchor).

## Official-generator weak types (bench 15, seeds 5119 and 2190, 61 cases each)

| Type | v8 | drp23v16 |
|---|---|---|
| absence-near-miss | 9/10 | 10/10 |
| absence-twin-false-premise | 7/8 | 8/8 |
| record-quantity-cf-base / cf-variant | 23/24 | 23/24 |
| world-story-quantity | 17/18 | 16/18 |
| others | equal | equal |

Run means: seed 5119 0.943 → 0.975; seed 2190 0.975 → 0.959. Gains are on declines; the losses are arithmetic slips
that flip between runs.

## Mock checks (free, 5 seeds, 1,750 cases matched by question text)

- **drp23v15b → drp23v16:** 2 changes. Two contact questions about a person no record names now take the records
  path, where the unnamed-person note lives.
- **drp23v16 → drp23v16r:** 17 changes. All are memory story questions already in the records lane; only the lane
  reason changes and the topic path stays. No tool case moves.
- Earlier "0 changes" claims matched by case id, which is randomized per run, so they compared nothing. Match by
  question text.

## The follow-up question (M43)

- It fires on 97 of 250 memory questions in v8's full trace and adds 2 calls each time (the question, then one more
  deciding turn). That is about 13% of memory-case calls, and the long ones.
- Nothing in the grader rewards it.
- It can ground a decline (it names people by every name), and it leaks distractors on list questions.
- It is a setting (`HARNESS_FOLLOW_UP=0`), so it can be A/B tested without a code change.
