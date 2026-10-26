# Record selection: dan0l v24 vs ours on competition seeds (2026-10-25)

## Method

- `lab/compare_selection.py`, five competition seeds (see `2026-10-25_router_on_competition_seeds.md`), 1,440 questions with labelled evidence.
- Each harness is followed offline from its own routing to the records its deciding model sees:
  - **dan0l:** `lab/select_dan0l.py`. Program path, topic path, contact-request topic path (M46), records-lane packet with meaning additions, or action-lane packet with topic records.
  - **Ours:** `lab/select_ours.py`, shipped settings. Topic path, program path, or records/action packet refilled from the fused lexical, embedding and full-text orders.
- Left out for both: the recall turn's pinned search hits (model) and the person reading on contact questions. The fallback is the cards of every person the thread names in full.

## Results

| | recall | full recall | precision | records | chars |
|---|---|---|---|---|---|
| dan0l v24 | 96.8% | 95.0% | 30.8% | 27.2 | 16,050 |
| ours | **98.7%** | **97.0%** | **32.4%** | 24.8 | 16,183 |
| memory questions (1220) | dan0l 97.2 / ours 98.8 | 96.0 / 97.2 | 34.4 / 36.5 | | |
| tool cases (220) | dan0l 94.5 / ours 98.0 | 89.5 / 95.9 | 10.4 / 9.9 | | |

Questions missing at least one needed record: dan0l 72, ours 43, both 28.

**Where dan0l is better:**
- "Current owner's work email" (`world-story-x-owner-email`, 65 questions): full recall dan0l 0.95, ours 0.74.
  - dan0l sends "Track down the current owner's current work email" to the topic path through its stored-detail rule (M46), with the people's contact cards: about 24 records.
  - Ours gives these questions a 30–50 record records-lane packet that misses the owner's contact record.

**Where ours is better:** these are the questions where the refill (fused embedding and full-text orders) brings in what dan0l's packet lacks.

| question type | dan0l | ours |
|---|---|---|
| "Which bank do I use now?" (retraction) | 0.40 | 1.00 |
| negation | 0.73 | 1.00 |
| as-of invoice totals | 0.75 | 0.95 |
| stale-removed handles | 0.60 | 0.80 |
| cross-user emails | 0.13 | 0.40 |
| tool cases | dan0l alone misses 9 "per what we agreed" routing cases and 4 note deletes; ours misses none of those | |

**Same in both:**
- **Topic paths:** 99% full recall. Ours shows 7.0 records against dan0l's 11.0 on our topic cases, because dan0l adds cards more often.
- **Program paths:** 100%.

## Contact details on a thread, taken from dan0l (`stored_detail_topic`)

A records-lane request with no identifier that asks for a contact detail, and that no short path took, now reads its thread on the topic path with contact cards. Our refill stays for everything else.

| | recall | full recall | precision | records | chars |
|---|---|---|---|---|---|
| ours before | 98.7% | 97.0% | 32.4% | 24.8 | 16,183 |
| **ours now** | **99.0%** | **97.9%** | **32.6%** | 24.6 | 16,092 |
| dan0l v24 | 96.8% | 95.0% | 30.8% | 27.2 | 16,050 |

- 15 questions changed path, all "current owner's work email". 13 gained full recall and none lost it.
- On that question type, full recall went from 0.74 to 0.94 (dan0l 0.95), with fewer characters (14,875 against 16,878).
