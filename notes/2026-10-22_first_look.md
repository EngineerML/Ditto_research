# SN118 Ditto, first look (2026-10-22)

Sources: official docs (`docs/official/`, published July), the `ditto-subnet` monorepo at 115ca38f
(2026-10-21), the public platform API (`live/2026-10-22/`), and chain data via btcli.

## What the subnet rewards

Miners submit an agent-memory harness: a Docker build context, any language, serving the public
harness HTTP contract on port 8080. Validators (up to three, median) run it in a sandbox against
DittoBench: a dataset regenerated from an on-chain block hash fixed after the miner commits, one
locked model for everyone, and a deterministic grader with no LLM judge.

```
composite = (0.5 x tool_mean + 0.5 x memory_mean) x efficiency x consistency x canary
```

Miners never serve live traffic and need no open ports. The work is retrieval and agent
engineering: embeddings, ranking, reranking, tool-call discipline, and prompting the locked model.

## The official docs are out of date

| | docs (July) | now |
|---|---|---|
| artifact | Rust crate from `dittobench-starter-kit` (archived 2026-08-11) | Docker build context, any language; reference kit in `ditto-subnet/miners/dittobench-starter-kit` |
| model | Qwen3-32B | `openai/gpt-oss-20b`, reasoning effort forced to medium (bench config) |
| benchmark | DittoBench V2 | bench v13 live (MINER.md still says v12 live, v13 shadow) |
| fee | ~$5 in TAO | 0.05 TAO (`/upload/eval-pricing`; MINER.md says 0.1 TAO as of 2026-09-14) |
| payout | champion ~90% | 50 / 20 / 13 / 10 / 7 to champion + next four (MINER.md says 65/14/10/7/4) |
| dethrone | ~5% | max(0.007, 1.64 x combined stderr), with incumbency defense |

Parameters move often (3,232 commits, about 1,000 a month in August and September). Read the
live API, not the docs.

## Live state

- 38 distinct miners on the leaderboard. Top composites 0.80-0.84, each with stderr about 0.02
  over three validator runs.
- Champion: uid 153 "Hades", 0.8043, crown since 2026-10-20 02:30. uid 149 "dan0l" sits at
  0.8440 and still does not dethrone: the required lead is 0.033 (statistical band), so the score
  to beat is 0.847.
- Ranks 2-5 are paid by raw rank and currently go to four other miners, so a strong non-champion
  still earns 7-20% of the miner pool.

## Chain and economics

- Alpha price 0.0043 TAO, pool 4.92k TAO / 1.14m alpha, market value 14.28k TAO.
- TAO emission into the subnet is 0 right now (net inflow EMA -0.0020 TAO), so value comes only
  from alpha emission, and alpha keeps getting sold into a pool that gets no new TAO.
- Rough miner pool, assuming the standard 1 alpha per block with 41% to miners: about 148 alpha per
  tempo, about 0.64 TAO at today's price, about 12.7 TAO a day. Champion 50% is about 6.4 TAO a day,
  rank 5 at 7% about 0.9 TAO a day. Not yet checked against on-chain incentive.
- Registration: min burn 0.0005 TAO, x1.26 per registration, half-life 360 blocks. Immunity is
  only 300 blocks, so a hotkey outside the paid five can be pruned quickly.

## Fit for us

- No latency race and no inbound ports: submission is HTTP plus one on-chain transfer, both of
  which work from this machine through the proxy.
- Practice costs model calls: leaderboard runs average about $0.98 of inference each. Local
  practice needs an OpenRouter (or local) key for gpt-oss-20b.
- Each on-chain attempt costs 0.05 TAO and is scored with about 0.02 noise, so prove a clear gain
  off-chain first.

## Next steps

1. Build and run the reference harness locally (`miners/dittobench-starter-kit`), get a baseline
   with `uv run ditto practice --run-size full` on gpt-oss-20b.
2. Read the scorer (`services/dittobench-api`, `research/dittobench-datagen`) and the bench v13
   gates in the starter kit README, then decide where the points are.
3. Check the payout estimate against on-chain incentive once `btcli` metagraph reads work.
