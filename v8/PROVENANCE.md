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
- `app/guide_records.py`, `NEXT_NOTE`: a next-step answer gives the person, the task and the channel
  even when the message names only the owner and the channel; the channel is the medium alone, and
  ordinary words are written correctly spelled.
- `app/short.py`, program path (one case file's entries):
  - copies of one statement filed in the same minute are shown once (`once_each`);
  - a ledger call reads the entries alone, without the message, under our general reading rules
    (`READING_RULES`: order, labels, separate matters, changes, going back, lists, plans, roles, dates,
    people, values) and writes each defined label, each change and what holds now; requests over the
    same notes share it;
  - the deciding conversation carries the ledger as the assistant turn it was written as, and the model
    answers from it in one plain sentence (`REPLY_NOTE`, `ANSWER_RULES`), replacing the release's chain
    note and its shared draft;
  - a later rewording of a question over the same notes reads the first rewording's question and its
    decided reply as the earlier turns of its conversation, then its own question; the model writes
    every reply, and the host never compares, retries or substitutes.
- `app/lane.py`, `app/agent.py`: a question that names a case file the user's records hold may take the
  program path even when it contains a word such as "news" or "web" (`own_records_question(held=...)`,
  set only by `short_answer`). The other checks are unchanged: naming a listed tool, a fetch from a
  tool, and a request that asks for an action.

The reused reply is the shape of the 2026-10-29 ruling on reused drafts (precedent
`october-29-reused-draft-no-disagree-clause`): a model-sampled reply enters the prompt only as text the
model reads.

The case-file ledger works the same way. It is a model completion, written from the case file's entries
alone before the deciding turn and shared by requests over the same notes. It is carried as the assistant
turn it was. No code reads, parses or selects anything from it. It is unrelated to the executor's
tool-call receipts, which dan0l's code also calls a ledger. `REPLY_NOTE` asks the model to answer from
the ledger it wrote, and the `ANSWER:` value is parsed only from the deciding reply, which the model writes
in full. We ask for this because the alternative measured worse. On our practice runs, a reply told it
could follow an entry over its own ledger re-read the raw sentences and repeated the misreadings the
ledger had resolved. It lost about two questions in forty and gave different answers to rewordings of
one question. Dropping only "which already applies every entry" moved the reply partway toward the same
errors.

Horizon v6 (agent b55c19f0-329d-459f-8de3-a887b8286606) is this harness without the program-path
changes above; it was held as a near-duplicate of dan0l v28 and released by the operator on
2026-11-01 after review against its PROVENANCE.md.

The model is the platform's (`openai/gpt-oss-20b` through the request's relay); no weights and no
benchmark data ship with the harness.
