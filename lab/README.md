# Offline lab

Tests routing and record selection designs against the official answer key, with no
chat-model calls. Datasets come from the official generator (`research/dittobench-datagen`
built to `.cache/dittobench-generate`), so a seed and surface salt give the same dataset a
validator builds. Production scores use a validator-held surface salt, so test on salts
the designs were not tuned on.

| file | what it is |
|---|---|
| `data.py` | dataset -> lab cases: text, user, the records held when the case runs, true lane, needed records |
| `embed.py` | embeddings on the validators' model (pplx-embed-v1-0.6b, 768 dims), cached forever in `.cache/embeddings.sqlite`, with a dollar cap |
| `meaning.py` | meaning search over whole records and over paragraphs of long records |
| `hades.py` | Hades v6's own lane rules and record pack, imported from `released/hades-v6_e6638d76/src` |
| `designs.py` | the routers and selectors being compared |
| `eval_offline.py` | runs them all and prints routing and selection tables; saves `results/*.json` |
| `run.sh` | runs a module with `.venv` and the proxy settings |

```bash
bash lab/run.sh lab.eval_offline --no-meaning                       # free
bash lab/run.sh lab.eval_offline --test 101,102,103 --test-salt 7   # ~$0.005 of embeddings
```

Ground truth used:
- lane: memory questions, and tool questions whose expected tools are only memory reads,
  belong in the records lane; other tool questions in the action lane; tool questions that
  expect no call are reported apart (the model has to read the records to get them right).
- needed records: memory = `v10_evidence_pair_ids`; tool = small prerequisite sets plus the
  records that hold a required argument value (an email, a pair id).

Setup once: `apt install python3.12-venv`, `python3 -m venv .venv`,
`.venv/bin/pip install pydantic==2.11.9 httpx==0.28.1 numpy`, and the Hades release
unpacked with `tools/fetch_release.sh`.
