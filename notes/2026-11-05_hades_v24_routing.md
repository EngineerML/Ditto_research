# 2026-11-05: Hades v24 (released) against our call count

Hades v24 (agent `a0fc00a9`, bench 14, released 2026-11-04 22:18 UTC, `released/Hades-v24_a0fc00a9`) is built on dan0l
v28. Its records engine is the same as ours: recall turn, timeline, reading, 3 drafts plus deliberation, the follow-up
question and 5 search passes (`drafts=3`, `search_passes=5` in its config). Its lower call count comes from routing.
Before that engine runs, `CaseRunner.run` (`app/agent.py`) tries several cheap paths:

1. `evidence_view` → `answer_from_view` (`app/short.py:935`): one deciding call over the short notes that name the
   thing asked about, each with its date, labelled not checked. It covers questions on:
   - an invoice or a partial payment;
   - a trip or trip leg;
   - a messaging handle;
   - a dated email, or "no email held".

   It was introduced in Hades v20 (released).
2. A `same_question` reply reuse: a reworded question over the same notes gets the earlier reply through one
   low-effort call.
3. `ShortPath` (a draft shared between rewordings, then a deciding call) and `TopicPath`. We have both.
4. `stored_detail_topic`, plus a `handle` lane for handle, stay-total, account-figure and contact-detail questions.

## Offline replay on our full-run seed

I ran Hades' own lane and path checks on every question of seed 6105760120852188829, with that user's records and no
model calls. I then matched each question by text to our run `20261104T154802Z_ditto-harness-drp23v16r_full`
(172 of 175 matched).

| Our expensive cases (≥ 6 calls): 73 cases, 751 of our 1,030 calls | Cases | Our calls |
|---|---|---|
| Hades: evidence view, 1 call | 28 | 230 |
| Hades: same full engine | 37 | 448 |
| Hades: action loop (tool cases) | 8 | 73 |

- **Moved to the evidence view.** These are absence questions (false premise, insufficient composition, pure, near
  miss, stale or removed, cross-user), point-in-time contact, invoice and trip-leg questions, world-trip-current and
  world-contact-previous. We spend 6–14 calls on each.
- **Kept on the full engine by Hades too.** These are enterprise-composed-program (12), world-isolation-contact-current
  (7), record-quantity-direction (4), some absence twins and injections.
- **Hades' path split for all memory cases:** full engine 39, topic 36, evidence view 31, action 11, short path 8.

Our scores on the movable types in that run were already high. All absence types scored 1.0, point-in-time contact and
invoice 1.0, and world-trip-current 1.0; trip-leg scored 0.5 and world-contact-previous 0.0. So the change is mostly a
cost cut. The risk is losing some of those 1.0s on a one-call path.

**Estimate.** About 200 fewer calls out of 1,030, roughly 20% of the datagen half's cost (about $0.82 → $0.66 at v16
rates), before the tool selector. This is rough: the replay approximates the short and topic paths, which can still
fall through after their model call.

The rerun that added our per-case scores to the replay was blocked by the session's auto-mode check. The first run's
path counts are shown above; the per-type scores come from our report alone.
