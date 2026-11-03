# Bench-15 atlas

A map of the SN118 bench-15 generator and a test bench for harness rules, built 2026-11-03 so that fixes are judged
on hundreds of seeds instead of the few a paid run covers. Everything here is free to rerun: no model call.

## Read first

- **The harness is served clean generator text, not the dataset file's text.** The dataset files (and the generate
  binary's `-out`) carry an extra typo pass that is only hashed (`services/dittobench-api/cmd/dittobench-api/main.go`
  1542-1571). On a real run 350/350 inputs equal the served dump, 119/350 the dataset text. Test rules on
  `.cache/served/`, never on dataset prompts. See `surface_noise.md` §0.
- **The surface salt does not reach a live bench-15 run.** The run path builds the salt-0 artifact; per run only ids
  (UUIDs) and case/record order change. Seed + salt 0, as served, is the live input.

## Files

| file | what |
|---|---|
| `tool_families.md/.json` | 84 tool categories: assembly (100 cases a run), frames, expected tools, grading, per-run counts, hazards |
| `memory_families.md/.json` | 50 question types (about 66 shapes with program sub-families): assembly (250 a run), evidence shapes, the grader's rules probed with about 40 reply styles, capped types, hazards |
| `surface_noise.md/.json` | what is noised and where, fillers, wordbanks, coined words, salt, characters, a 16-item fragility checklist |
| `static_<tree>.md/.json` | static bench of a lab tree: connector step, first-stage lane, request kind, product note, live, qtype per family (200 seeds, 70,000 requests) |
| `mock_<tree>.md/.json` | mock bench: the harness's final lane and path per family (40 seeds, 14,000 requests) |
| `corpus_seeds.txt` | the 200 corpus seeds (the first 43 are the earlier cached ones) |

## Rebuild and rerun

```
python3 v15_atlas/gen_corpus.py                 # datasets for metadata and catalogs (.cache/datasets)
bash v15_atlas/build_served.sh                  # served text (.cache/servedgen, .cache/served)
bash v15_atlas/run_static.sh                    # static bench of drp23v15 and drp23v15b, then summaries
python3 v15_atlas/static_compare.py .cache/atlas/static_A.jsonl .cache/atlas/static_B.jsonl
TAG=<image> N=40 bash v15_atlas/run_mock_bench.sh && python3 v15_atlas/mock_summary.py v15_atlas/mock_runs_<image>.txt v15_atlas/mock_<image>
```

Rule for every harness change from here on: it must pass the static bench (all 200 seeds, served text) and the mock
bench (40 seeds) with no unexplained change before any paid run; a paid A/B then only confirms model behaviour on
the cases the bench says it reaches.

## What the bench says now (drp23v15b against v8)

- Connector step: 200 tools left out on all 70,000 requests, none kept as linked.
- Product notes on the wrong tool: 71 (v8) → 4 (drp23v15b) over 200 seeds; right ones 1,998 → 2,000. The fix holds on
  served text.
- Final lanes (mock bench): nearly every family lands where its expected tools or answer form point. The rest:
  conversational-declarative, parser-divergence-hypothetical and world-canary go to the action lane every time (their
  answers still come from the records packet; hypothetical scored 3 of 3 in our runs); chitchat 28%;
  injection-data-inside-envelope 19% (4 records a run tell the model to call `gmail_send`); capability_discovery
  reaches the records lane 5%.

## Findings that generalise (from the three maps; details in each file)

1. Same words, different answer: 255 normalised prompts map to two or more tool sets (4,027 cases over 200 runs),
   because a stored record decides the move. Wording-only routing cannot be right on these; the records must reach the
   deciding turn.
2. Keyword cues point the wrong way by design: every update prompt uses delete/save words and every delete prompt
   update/save words; "remember" leads to delete 158, update 137, save 57; "email" leads to delete_memory more often
   than to gmail_send.
3. Look-alike tools: in 56% of decoy-correct cases a connector with the same capability is in the catalog; only the
   coined brand tells them apart (v8's connector step removes those connectors).
4. Coined brands: about 2% are English words and a lower bound of 12% are one edit from one (estimates); a product
   rule must not match lower-case prose.
5. Grading (memory): a decline phrase anywhere in an answerable reply scores 0 (16 phrases probed); a correct slot
   with no matching prose scores 0; money has three conventions by family (cents in expected_answer but dollars in
   the reply for invoice/outstanding; major units of the asked currency for record-quantity; bare integers as cents
   for story quantity); only some time formats pass ("14.30" and "2.30pm" fail); list separators are equivalent.
6. Structurally capped for an honest reader: parser-divergence negation/retraction/reported-speech (1 of 3), chitchat
   (0.5 cap), conversational-declarative (0.25 without the stated value).
7. Record layout: all world/story/absence/point-in-time evidence sits in the tool cases' prerequisite pairs (about 369
   a run), loaded before everything; 54% of served records share an identical response with more than two others;
   records reach 18,276 characters.
