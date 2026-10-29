# Provenance

This harness is built on dan0l's released source, v28 (agent b4b99c40-151a-4792-a814-9fad4f9d2f9c,
artifact sha256 de97219a76e616a95487b9ade47e7f946793d43be0a3ba9bcdab78520e94b792, released
2026-10-28), which SN118 publishes after its embargo and permits building on. Everything not listed
below is dan0l's code as released. Our changes:

- `app/short.py`, program path: the notes of a case file are shown with their filing dates and in
  the order they were filed; the order reading only orders notes filed at the same moment, and when
  it fails the notes keep their filing order and the request stays on this path. v28's reordering of
  self-marked changes (and its note that filing dates do not show the order) is removed.
- `app/short.py`, program path: the prompt says how notes that change what holds are read (the
  latest note about a thing holds, a withdrawn entry leaves the one before it in force, going back
  to a previous entry restores it, one time can be written two ways). The model reads the notes and
  decides.
- `app/short.py`, `app/agent.py`: when the same user asks the same question of the same notes again,
  the first request's reply is shown to the deciding model as a note it may give again or replace;
  every request is decided by the model from its whole message.
- `app/llm.py`, `app/config.py`: any failure of a model request is retried like a transport failure,
  and a request hanging at the provider is given up after 60 s instead of 100 s.
- `app/memory/final_check.py`: the final check's reply keeps its `ANSWER:` line.

The model is the platform's (`openai/gpt-oss-20b` through the request's relay); no weights and no
benchmark data ship with the harness.
