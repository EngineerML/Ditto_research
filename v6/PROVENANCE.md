# Provenance

This harness is built on dan0l's released source, v30 (agent 95534e25-052c-4dd4-943e-39b3cff95e13,
artifact sha256 29cf12e6ac4659472e339d7809d269efe7e54232e7fde182b8509ae68da5f960, released
2026-10-31), which SN118 publishes after its embargo and permits building on. Everything not listed
below is dan0l's code as released. Our changes:

- `app/llm.py`, `app/config.py`: any failure of a model request is retried like a transport failure,
  and a request hanging at the provider is given up after 60 s instead of 100 s.
- `app/memory/final_check.py`: the final check's reply keeps its `ANSWER:` line.

The model is the platform's (`openai/gpt-oss-20b` through the request's relay); no weights and no
benchmark data ship with the harness.
