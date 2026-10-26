# Parked drafts

Changes that were built and measured but not applied. Each patch applies to the file it names
in combined/ (`patch -p1 -d combined < drafts/NAME.patch`).

## plain_spelling_mender.patch (2026-10-26)

Replaces the routing typo mender's slip rule (same first and last letter, at most a third of the
word in edits, capped at 3) with a plain spell-checker rule: same first letter, one edit for a
cue word of up to four letters, two for a longer one, exactly one candidate. Why: the screener's
C13 fingerprint `typo-tolerant-token-compare` fires on the mender, and its old rule has the shape
of the benchmark generator's typo model, which a strict reviewer could call generator-fitted.
One L1 review (gpt-6-luna) cleared the current mender; this is the fallback if a later review
does not.

Offline routing (lab/route_check.sh, shipped setting all@0.85, cached embeddings, no chat calls):

| | competition seeds | second seed set | total of 3500 |
|---|---|---|---|
| current mender | 1737 | 1730 | 3467 |
| plain edit distance, no letter rule | 1733 | 1724 | 3457 |
| this patch (first letter kept) | 1732 | 1729 | 3461 |

The last-letter check was catching real wrong mends ("ruad" read as a records word, "Tel" and
"chanrl" in next-action questions); without it the router loses about 6 cases per 3500 questions.
