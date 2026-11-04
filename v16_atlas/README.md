# v16 atlas: tool-list selection for bench 16

Bench 16 lists about 235 tools on every request: the product tools plus about 200 connector tools of about 120 apps.
Connectors no longer say whether they are linked. Each turn that carries the whole list pays about 7,100 prompt
tokens for it, and v16 multiplies the score by a priced-cost factor (`1 − 0.4 × (cost − $1)`, floor 0.6 at $2).
horizon v8's v16 runs cost $1.52 (factor 0.79), and most of that is prompt tokens.

`toolselect.py` keeps every tool a request can plausibly need and leaves out app tools nothing in the request points
to. It reads only the request's text and each tool's own name and description. The rules are in its docstring:
general tools (including mail and the calendar) are always offered; an app's tools are offered when the request names
the app.

## Files

| File | What it is |
|---|---|
| `servedgen/main.go`, `build_served.sh` | Dumps what the bench-16 scorer serves for each corpus seed (case text before the typo pass, the seed's catalog) to `.cache/served16/v16_s<seed>.json`. Expected tools and the connector plan are included for the bench only. |
| `corpus_seeds.txt` | The 200 seeds of the v15 atlas corpus. Even lines are the dev half, odd lines the test half. |
| `toolselect.py` | The selector, written to drop into the harness unchanged. |
| `select_bench.py` | Recall and size over the dumps, per half. `--json` writes the result. |
| `select_test.json` | The test-half result. |

## Result (2026-11-04, datagen f220cecd)

| Half | Tool cases | Recall (cases / expected tools) | Tools offered (tool / memory cases) | Prompt tokens per call |
|---|---|---|---|---|
| dev (tuned on) | 5,000 | 100% / 100% | 31.0 / 30.1 (max 38) | 1,365 (catalog 7,129) |
| test (held out) | 5,000 | 100% / 100% | 31.0 / 30.1 (max 38) | 1,363 (catalog 7,128) |

- The typo'd dataset text (20 test seeds × salts 0–2, 3,000 tool cases) also gives 100% recall.
- Token figures are 0.13 × each tool's JSON characters, measured on paired 36- and 235-tool calls of 2026-11-03.
- Every linked-connector, unlinked-probe and decoy case names its app, and the selector keeps that app's tools.
- The one need a request reaches without naming the app is mail and the calendar ("send them the numbers", "put it on
  my schedule"); those tools are general.

## How the rules were found

- **A + B only** (general + named apps): 93.6% recall on dev. Every miss was `gmail_send` or `calendar_create_event`
  (requests never say "Gmail"), plus possessives ("Fupupan's documentation").
- **Mail and calendar as general, possessives stripped:** 100%. Brand reading then widened (`monday.com`, `1Password`,
  "MongoDB Atlas", "Google Cloud" for `gcp`) to keep about 16 connectors out of the general set: 46.8 → 31.0 tools.
- A word-overlap tier for unnamed app tools added 4.5 tools a request (up to 139) and nothing that A + B with the
  channel rule did not already cover, so it was dropped.

## Expected effect

About 870 of a v16 run's ~1,111 model calls carry the catalog. Cutting it from about 7,100 to about 1,350 tokens saves
about 5.0M prompt tokens a run, or about $0.35 at the v16 rate: $1.52 → about $1.16, factor 0.79 → about 0.94, with
the same calls. The generator half's memory cases get the same ~30 general tools.

## Rebuild

```bash
bash v16_atlas/build_served.sh
python3 v16_atlas/select_bench.py --half dev
python3 v16_atlas/select_bench.py --half test --json v16_atlas/select_test.json
```
