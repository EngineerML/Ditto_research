# 2026-11-01 — DrPresident v20 released: its program path against v6

DrPresident v20 (agent 541b701a, sha 9f0cb252…) came out at 2026-11-01 04:17 UTC, as promised. It is in
`released/DrPresident-v20_541b701a`. Still held: v22 (until 2026-11-01 23:29 UTC) and the champion v23
(until 2026-11-02 18:41 UTC). dan0l v31 is awaiting emissions.

The line comes from dan0l v21, not v28–v30, so it is not a base for us. What is useful is its program
path, which v19 and v20 rebuilt (v17, the release before, has none of it). It covers most of the general
fixes proposed in notes/2026-11-01_v14_generator_review.md.

## Public program scores (3 provisional runs each, different seeds)

| agent | composites | open-program | personal-program |
|---|---|---|---|
| DrPresident v20 | 0.954 / 0.906 / 0.947 | 0.990 | 0.931 |
| DrPresident v22 | 0.943 / 0.971 / 0.930 | 0.927 | 0.931 |
| DrPresident v23 (champion, held) | 0.964 / 0.964 / 0.936 | 1.000 | 0.986 |
| dan0l v30 | 0.954 / 0.955 / 0.919 | 0.896 | 0.972 |
| dan0l v31 | 0.945 / 0.950 / 0.947 | 0.917 | 0.958 |

Three runs on different seeds can't rank v20 against v30 on program questions. v23's 1.000 / 0.986 is the
number to explain once its code is out.

## v20's program path (`app/short.py`), what v6 lacks

1. **One copy per statement.** `one_copy` shows copies of one statement filed in the same minute once
   (the copy whose words the others share most). The generator files every row three times, once per
   renderer, so the model reads a third of the notes. v6 shows all of them.
2. **State reading SR, notes only.** One advisory call per program request reads the filed notes without
   the message and writes one line per tracked item: item, what is tracked, the value now, the marks it
   rests on. Its rules: a later note replaces; struck, mistaken or declined leaves the value before it;
   going back restores the value just before the change it undoes; a list holds every item now; a plan
   gives each step open or closed with its owner. The text goes beside the notes under a "not checked;
   the notes decide" header. Nothing is shared between requests, but the input carries no message, so all
   three rewordings get the same input at temperature 0, seed 42. This is our G3, as a separate call, and a
   consistency anchor without any sharing.
3. **Reading rules in the program system text:**
   - `CORRECTION_RULE` (correction and revert);
   - `ONE_VALUE_RULE` (one value; the final holder alone);
   - `LIST_RULE` (the whole current list);
   - `AFTER_RULE` ("after the change / swap / every handover" means now, never one value per change: our
     G2);
   - `FORM_RULE` (closing line only shapes; an action as the notes word it, without the question's words:
     part of G4);
   - `STEP_RULE` (process steps);
   - `EVENT_DATE_RULE`.

   Its no-record sentences are taken out on this path.
4. **Closing host note after the message (`PROGRAM_NOTE`).** It says to give the value after the last
   change, never one per change. It adds: "after A, then B, then C, going back to the previous one leaves B,
   not C", and a struck entry leaves the value before it. Our F2 gave the rule without the worked example
   and got 0/9.
5. **The final check (FC) still runs on the short path,** with no limit. v6 runs it only when the reply
   has no ANSWER value (F1), because a full check flipped right answers.
6. Sampling is temperature 0, seed 42, as in v6.

## What it means for v6

- These items match three of our four weak shapes:
  - revert-to-middle: the worked example and SR;
  - identity contact "after every reassignment": `AFTER_RULE` and `PROGRAM_NOTE`;
  - membership "after the school's change": `AFTER_RULE`, `LIST_RULE` and SR.
- "pause it before then" is only partly covered: `FORM_RULE` keeps the notes' own wording, which may
  still include "before then".
- Released code may be built on. Candidates to take into v6's program path, each tested only on the
  shapes it reaches:
  - `one_copy`;
  - a notes-only state reading;
  - the A/B/C worked example;
  - the after/list/one-value rules.
- G1 (passing the first checked reply to the other rewordings, as prompt text only) stays our own
  addition. v20 gets its steadiness from identical inputs instead.
- v23 (held until 2026-11-02 18:41 UTC) scored best on program questions. Read it before choosing.
