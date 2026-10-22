<!-- source: https://heyditto.ai/docs/mining-on-ditto.md, saved 2026-10-22 -->

# Mining on Ditto (Subnet 118)

> Ditto is Bittensor Subnet 118. Miners submit an agent-memory harness; validators score it on tool-calling accuracy and memory recall against a fresh dataset; the best harness earns the emissions. Start here.

---

# Mining on Ditto (Subnet 118)

Ditto runs a Bittensor subnet: **SN118**, `netuid 118` on finney. The subnet rewards exactly one thing: **the best agent-memory harness.** You submit a small program that gives an AI agent a memory (the ability to store what a user tells it and recall the right thing at the right time) and validators score how well it calls the right memory tools and recalls the right memory. The strongest harness holds most of the emissions, with a small participation tail for the rest of the field.

> **Mining is going live on SN118 in July 2026.** You can build and practice today; this section walks you from a fresh fork to a live, scored submission so you're ready on day one.

## The 60-second version

1. **Start from the [DittoBench starter kit](https://github.com/ditto-assistant/dittobench-starter-kit)** (a Rust harness built on the [`ditto-harness`](https://github.com/ditto-assistant/ditto-harness) crate) and make it better at storing and retrieving memories.
2. **Practice off-chain** with DittoBench and the starter kit: the exact scoring loop, on fresh datasets, no TAO required.
3. **Submit on-chain**: pay a small fee, upload your harness tarball, and it enters the evaluation queue.
4. **Get scored**: validators run your harness in an isolated sandbox against a fresh, anti-cheat dataset and post signed scores.
5. **Win**: emissions concentrate on the top harness. Iterate and resubmit to climb.

## What you're building

An **agent-memory harness**: a **Rust crate** that implements Ditto's memory contract, the memory tools (save a memory, search memories, search subjects, fetch by id, search within a subject) and an importable agent loop. That interface is what validators exercise. Everything behind it (how you embed, rank, fuse, and rerank memories) is where you compete.

The [DittoBench starter kit](https://github.com/ditto-assistant/dittobench-starter-kit) is your starting point: a Rust crate that depends on the [`ditto-harness`](https://github.com/ditto-assistant/ditto-harness) crate and already ships a working pipeline (vector search → composite ranking → cross-encoder rerank) with the real ranking models. Start there, beat the baseline.

**You submit the whole crate.** `baseline.rs` is the marked starting point (the one file that wires everything together) but nothing limits you to it. You're free to change the reranker, retrain or swap the ranking models, rewrite the tools, restructure the crate: anything, as long as it builds in the sandbox and satisfies the harness contract.

## The pieces

| Piece              | Role                                                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| **Your harness**   | The Rust crate you submit, built on the DittoBench starter kit (which depends on `ditto-harness`).                          |
| **DittoBench**     | The benchmark + scorer that grades a harness on a fresh dataset. Available as a hosted practice API and in the starter kit. |
| **Ditto Platform** | The team-operated API that takes your submission, verifies your payment on chain, stores it, and tracks its status.         |
| **Validators**     | Independent operators who run your harness in a sandbox, score it, and set weights on chain.                                |
| **The chain**      | Bittensor settles registration, payments, and weights.                                                                      |

## What you need to submit

- **A registered hotkey on `netuid 118`.** Every submission is checked for registration: an unregistered hotkey can't submit.
- **A funded coldkey.** The submission fee is a small on-chain transfer (targeting ~$5 in TAO) signed by the coldkey that owns your hotkey.
- **A harness crate that builds and runs** inside an isolated Docker sandbox, packaged as a gzipped tarball **up to 20 MiB** (enough for the crate plus the shipped ranking models).

## Where to go next

- **[Start Mining: From Fork to Live](/docs/mining-getting-started)**: the hands-on path, including off-chain practice.
- **[Submitting to Subnet 118](/docs/mining-submitting)**: exactly what happens when you submit, step by step.
- **[Scoring & Rewards](/docs/mining-scoring)**: how DittoBench scores you and how the winner is chosen.

## Related

- [`dittobench-starter-kit`](https://github.com/ditto-assistant/dittobench-starter-kit): the Rust harness you start from + the offline practice loop
- [`ditto-harness`](https://github.com/ditto-assistant/ditto-harness): the crate the starter kit builds on
- [Memory Network](/docs/memory-network): how Ditto's memory works, end to end