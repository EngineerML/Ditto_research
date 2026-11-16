# 2026-11-16 bauni v6 (season 26126 c2): referring turns

## Source and packs
- Released 2026-11-16 05:33 UTC: submission `41a497e8`, hotkey 5CvZx4ZU, archive sha256 `e82bd049…` (matches `source_sha256`).
  Downloaded to `.cache/miner_gens/dl/bauni-v6_41a497e8`; its internal generator name/version is "bauni 12".
- Packs 1–3 in `.cache/miner_gens/packs/bauni6` (`live/build_bauni6.sh`, no-network sandbox, bench 18), 35 `coref-mix` cases each.

## Case shape (`gen/coref.go`, "split-message lists")
- "Which two cafes does <Full Name> go to every week?" One item is under the full name ("X is at A every week").
- The other item is in the note right after a lead naming the person, in the same session, 41 minutes later:
  "Shared a taxi home with X after the party." then "The person I shared the taxi with spends every week at B."
- 12 leads in all, such as lunch companion, taxi, wedding, dog walk, train, helped move, school gates, pub quiz, lift, post office queue, station lift and parents' evening.
- The two distractors are the same kind of relay after leads about other people.
- crown-v228's same-conversation follow-ups stop at 20 minutes, so the relay was never seated. Our tree (37bd158) answered only item A in every case.

## Fix: `referring_turns` (`app/packet.py`, called in `app/records.py`)
- After a packet record writing the asked full name, the next turn of the same session is seated right after it, whatever the gap, when it names nobody and opens with a referring phrase (`REFERS_BACK_RE`).
- The entry carries `sameConversationAs` and `phraseMeans`.
- A note before the message names each such mark ("M16 speaks of X: it is the next turn after M15").

## Static check (free): `practice/c228_referring_reach.sh`
- bauni v6: 105/105 cases reached, the evidence relay seated in every one, no distractor ever seated.
- No case reached in the 4 v18 datagen seed sets or any other local pack (2,950 cases).
- Earlier pattern drafts caught "The train was twenty minutes late", "My colleague Nadezhda …" and "My neighbor's dog …". The final pattern rejects all three.

## Paid (grader-normalised tally, `practice/list_tally.py`; U+202F counts as a space, as in the grader's `strings.Fields`)

| Agent | pack 1 | pack 2 | pack 3 | mean |
|---|---|---|---|---|
| 37bd158 (nt2) | 0.50 | | | 0.50 (official c2 0.50) |
| dan0l v59 | 0.66 | | | 0.66 (official 0.68) |
| seated only + general note | 0.69 | 0.61 | 0.70 | 0.67 |
| + `phraseMeans` field | 0.86 | 0.84 | 0.90 | 0.87 |
| + per-mark lines (final) | 0.91 | 0.89 | 0.96 | **0.92** |

- No distractor was named and no reply declined.
- Runs: `practice/generator/20261116T085747Z`, `…091443Z`, `…092706Z`, `…094046Z`. Run `…090529Z` crashed (a NameError, fixed).
- Cost about $0.19 in all (balance $13.18).
- Leaders on this column score 0.97–1.0.
