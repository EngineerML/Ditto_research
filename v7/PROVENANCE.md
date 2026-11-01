# Provenance

This harness is built on dan0l's released source, v30 (agent 95534e25-052c-4dd4-943e-39b3cff95e13,
artifact sha256 29cf12e6ac4659472e339d7809d269efe7e54232e7fde182b8509ae68da5f960, released
2026-10-31), which SN118 publishes after its embargo and permits building on. Everything not listed
below is dan0l's code as released. Our changes:

- `app/llm.py`, `app/config.py`: any failure of a model request is retried like a transport failure,
  and a request hanging at the provider is given up after 60 s instead of 100 s.
- `app/memory/final_check.py`: the final check's reply keeps its `ANSWER:` line.
- `app/short.py`, `app/records.py`: on the program path the final check runs only when the decided
  reply has no `ANSWER:` value; a reply that gives its value ships as the model decided it.
- `app/short.py`, program path (one case file's entries):
  - copies of one statement filed in the same minute are shown once (`once_each`);
  - a ledger call reads the entries alone, without the message, and writes how each tracked value
    changed; it goes beside the entries as unchecked text, and requests over the same notes share it;
  - our own reading rules for change records (`LEDGER_RULES`) and a closing note after the message
    replace the release's chain note and its shared draft;
  - a later rewording of a question over the same notes reads the first decided reply beside the
    notes, as text; the model writes every reply, and the host never compares, retries or substitutes.
- `app/guide_records.py`, `NEXT_NOTE`: a next-step answer gives the person, the task and the channel
  even when the message names only the owner and the channel; the channel is the medium alone, and
  ordinary words are written correctly spelled.

The model is the platform's (`openai/gpt-oss-20b` through the request's relay); no weights and no
benchmark data ship with the harness.
