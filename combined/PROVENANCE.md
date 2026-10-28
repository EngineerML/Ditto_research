# Provenance

This harness is built on dan0l's released source, v24 (agent ecf5a1a2, released 2026-10-25), which
SN118 publishes after its embargo and permits building on. Its served path, the two lanes' model
loops, retrieval, store, tool executor and response shaping, is dan0l's code. Our work on top of
it:

- `app/ours/lane.py`, `app/ours/meaning.py`, `app/ours/intents.tsv`, `app/ours/words.txt`: our
  router (word rules with misspelled cue words mended for routing only, a meaning router over
  hand-written example requests, overrides for the user's own records and product questions).
- `app/ours/guidance.py`: advisory notes for the action lane, chosen from the request's wording
  and the tools the catalog offers, placed after the request; a request that gets a note is
  handled on the action lane. The model sees the whole request, records and catalog and makes
  every call; nothing is forced or rewritten.
- `app/agent.py`: routing with the above, and packets refilled from fused lexical, meaning and
  full-text orders.
- `app/packet.py`, `app/records.py`: `fused_rank`, `refill` and person cards (records of the
  people a request names, nicknames included).
- `app/short.py`: the topic path's prompt and record choice, including a sentence asking for a
  worked-out figure alone on the answer line; on the program path, notes ordered by their filing
  dates (the order pass only orders notes filed at the same moment), and one answer for the same
  user asking the same question of the same notes again, the first request's own reply.
- `app/action.py`: the notes' placement, the checks reading the request alone, and a cut-off
  turn asked again at the same effort with more room.
- `app/tools.py`, `app/records.py`: after a note is kept or updated, and when the user only states
  something to keep, the model is asked to say back in its own words what was kept.

The model is the platform's (`openai/gpt-oss-20b` through the request's relay); no weights and no
benchmark data ship with the harness.
