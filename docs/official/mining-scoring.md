<!-- source: https://heyditto.ai/docs/mining-scoring.md, saved 2026-10-22 -->

# Scoring & Rewards

> How Ditto SN118 scores a harness: a fresh anti-cheat dataset every run, one frozen model, a judge-free composite of tool accuracy and memory recall scaled by integrity gates, multiple validators finalizing on the median, and king-of-the-hill emissions.

---

# Scoring & Rewards

When your submission reaches `evaluating`, validators run it through **DittoBench** in an isolated Docker sandbox and post signed scores. This page explains how the number is computed and how it turns into emissions. For the benchmark's full internals, see [DittoBench V2: Rebuilt Every Run](/blog/dittobench-v2-the-benchmark-that-rebuilds-itself).

## A fair, anti-cheat run

Three design choices make scoring fair and hard to game:

- **The dataset is regenerated for every run.** Every case is produced from a single seed: tool cases are paraphrased and the memory "haystack" is reassembled with distractors and fresh timestamps, so there is no static answer key. The benchmark version is mixed into the seed, so the surface wording rotates when the version changes and an agent tuned to one version's phrasings degrades on the next. Memorizing the benchmark does not help; only a genuinely good memory pipeline scores well.
- **One frozen model for everyone.** Validators score every harness on the same locked model, **Qwen3-32B**, so you compete on your memory and tool logic, not on who wired up the strongest LLM. Practice against the same model for comparable numbers (see [Start Mining](/docs/mining-getting-started)).
- **Multiple validators, median score.** Several assigned validators each run your harness on their own seed and post a **signed** score. The result is finalized on the **median**, and every validator recomputes weights from the same public ledger with the same open-source function, so no single validator decides your fate.

## The composite score, no LLM judge

Grading is fully deterministic. There is no language-model judge: the generator knows the ground truth of every case it invents, so it emits a typed answer key and grades by rule. Your score can be recomputed by anyone from the recorded seed and transcript.

Each run produces a composite in `[0, 1]`:

```
composite = (0.5 × tool_mean + 0.5 × memory_mean) × efficiency × consistency × canary
```

- **`tool_mean`**: tool-calling accuracy: `0.4` correct tool selection, `0.4` correct arguments, `0.2` order and call discipline. Both missing a needed call and making extra ones lose points. The mock tool server is run by the grader, so tool use is observed rather than taken on trust: a harness that skips the server and self-reports its calls is capped at `0.5` on the affected cases.
- **`memory_mean`**: memory recall, graded by typed answer kind (value, number, list, ordered list, duration, activity, decline, and so on) with normalized matching against the answer key. Surfacing another user's fact, a decoy value, or declining an answerable question scores that case zero.
- **Integrity gates**: `efficiency`, `consistency`, and `canary` are bounded multipliers on the whole composite. `efficiency` penalizes burning far more tool calls than a case needs; `consistency` (metamorphic) checks that semantically equivalent phrasings get the same answer; `canary` guards a planted bait value (echoing the bait multiplies by `0.5`, an honest miss by `0.85`). They scale the composite; none zeroes the run.

The same composite is what you see when you practice off-chain with the [starter kit](https://github.com/ditto-assistant/dittobench-starter-kit), so your practice number and your on-chain number are directly comparable.

## Latency is not scored

Wall-clock time depends on the validator's hardware and the model provider's load, none of which your submission controls, so it is deliberately left out of the composite. Latency and token counts are still recorded and published as telemetry, so a slow harness is visible. What the composite scores instead is call discipline: the `efficiency` gate penalizes wasteful tool use, which is the behavior a latency score was mostly a proxy for, without importing the noise.

## From score to emissions: king-of-the-hill

Emissions concentrate on one champion, with a small participation tail. This is a benchmark race, not a participation pool.

- **Champion.** The current best non-duplicate submission holds about **90%** of emissions until something dethrones it.
- **Dethroning gate.** A challenger takes the crown only by beating the champion by more than an indifference band: a flat margin of about **5%**, widened by the measurement noise of both scores. A challenger inside the noise, or a copy that merely ties, cannot flip the crown on a lucky seed.
- **Participation tail.** The remaining emissions spread over the next few distinct, non-duplicate submissions, so the field does not hollow out to a single earner.
- **Copies earn nothing.** First-seen timestamps plus plagiarism and near-duplicate detection protect the original author, so resubmitting the current best verbatim does not pay.

Only positive composites earn weight. The score ledger is public, so you can always see where you stand and by how much you need to improve. Exact tail economics may be tuned around launch; the [incentive mechanism](https://github.com/ditto-assistant/ditto-subnet/blob/main/docs/incentive-mechanism.md) has the current parameters.

## How to climb

- **Raise recall first.** `memory_mean` and `tool_mean` are where the points are. Better embeddings, ranking, subject handling, and reranking all move these.
- **Mind call discipline, not the clock.** Latency is not scored, but the `efficiency` gate is: do not spend far more tool calls than a case needs.
- **Measure on `full` before you submit.** Small runs are for fast iteration; a `full` practice run against Qwen3-32B is the closest proxy to an on-chain evaluation.
- **Beat the margin, not just the champion.** A tie or a noise-level edge will not dethrone the king; you need a real improvement past the 5% band.
- **Resubmit to climb.** Each submission is a fresh, independent evaluation, and each on-chain submission costs a fee, so prove it off-chain first.

## Related

- [Start Mining: From Fork to Live](/docs/mining-getting-started): practice against this exact score
- [Submitting to Subnet 118](/docs/mining-submitting): how to get into the evaluation queue
- [Mining on Ditto (Subnet 118)](/docs/mining-on-ditto): the overview