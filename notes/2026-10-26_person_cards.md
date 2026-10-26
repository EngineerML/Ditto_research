# Records lane: nickname records for the people a question names (combined, 2026-10-26)

## Why

Selection losses in the combined full run were mostly one shape: the question names a person in
full ("Tamra Schaefer") and the record holding the answer calls them only by the nickname another
record gives them ("Pip goes by jihehu_2773 on Signal"). A search on the question's words never
reaches it. dan0l's people cards (memory/people.py) follow that link, but only on the topic path.

## Change (combined/app/packet.py person_cards, called in records.py after the refill)

For each full name in the question, the short records (< 400 chars) that use one of that person's
nicknames and never the full name are added when the packet lacks them: newest first, at most 6
records and 2400 chars, never enough to make the packet "long". A nickname another person also
carries is skipped, and so is a record where the nickname starts someone else's full name.

Rules: records are only added (I2/W3); nothing rewritten, no tool change.

## Testing (practice/cards_fix, all on the subset scorer with writes replayed)

- v1 used dan0l's cards_for as is (full-name records too, both directions). On the pinned cheap
  providers it fired on 10 of 66 reachable questions; one loss was its own: "Jake" (Jacob Tran's
  nickname) matched "Jake Baca", another person. The 6-record cap also filled oldest-first and
  could cut a later "retired their Signal handle" record.
- v2 (kept): nickname-only records, collision and shared-nickname guards, newest-first cap.
- On the platform's own provider choice (throughput sort, mostly Amazon Bedrock), one run each over
  the 66: base 0.939, v2 0.924, the flips all on questions where cards did not fire (identical
  prompts, sampling). Then only the 13 questions where cards fired, 3 runs each side:

| 13 questions | base | v2 |
|---|---|---|
| mean score | 0.897 | 0.923 |
| regressions / gains | | 1 / 1 |

  The regression (c3b5b2c) never had cards added; its handle record was in every packet and one
  run declined anyway. The gain is the removed-handle question (ccc23ba, 0/3 -> 2/3): the cards
  bring in "Jazz retired their Signal handle", and the answer becomes "none".

The effect is small (on Bedrock the recall turn usually finds the nickname record itself): a net
for when recall misses, under one question per full run.

## Speed and cost of the test

Platform providers: median 2.8 s per call against 6.7 s on the pinned list; a 66-question
records-lane run takes 22 min instead of 55 and costs about $0.40 instead of $0.20. A 13-question
run costs about $0.09.
