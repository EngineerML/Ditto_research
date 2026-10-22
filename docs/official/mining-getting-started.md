<!-- source: https://heyditto.ai/docs/mining-getting-started.md, saved 2026-10-22 -->

# Start Mining: From Fork to Live

> The hands-on path to mining Ditto SN118: fork the reference harness, practice off-chain against DittoBench on the same frozen model validators use, then submit on-chain when your score is strong.

---

# Start Mining: From Fork to Live

This is the practical path from a fresh checkout to a live, scored submission. The golden rule: **practice off-chain until your score is strong, then pay to submit on-chain.** Practice is free and uses the exact same scoring loop, so there's no reason to spend TAO on a harness you haven't measured.

## 1. Start from the starter kit

Fork the [`dittobench-starter-kit`](https://github.com/ditto-assistant/dittobench-starter-kit): a complete, working **Rust** harness that depends on the [`ditto-harness`](https://github.com/ditto-assistant/ditto-harness) crate. It already implements the contract validators score:

- the memory tools: `save_memory`, `search_memories`, `search_subjects`, `search_memories_in_subjects`, `fetch_memories`
- an importable **agent loop** that uses them
- the full production retrieval stack, wired and active: vector candidate pool → composite ranking (multiple signals + a learned fusion-weight MLP) → cross-encoder rerank

**`src/baseline.rs` is where you start**: it's the marked extension point that wires the DB, embedder, model, ranker, and reranker together. But you submit the **whole crate**, so nothing limits you to it: change `reranker.rs`, retrain or swap the ranking models in `fixtures/models/`, edit the tool catalog, add files, anything that raises recall and tool accuracy without wasting tool calls (the efficiency gate is the one call-count check that touches your score).

## 2. Practice against DittoBench (off-chain, free)

The [`dittobench-starter-kit`](https://github.com/ditto-assistant/dittobench-starter-kit) is the official practice bench. It runs the **same generate → seed → run → score loop** the on-chain validators use, but off-chain and with your own model key:

- **Bring your own key**: supply a model API key per run; nothing is stored. On-chain, validators score every harness on a frozen **Qwen3-32B**, so point your key at that same model (for example `qwen/qwen3-32b` via OpenRouter, or a local Ollama or vLLM) to get practice numbers that match the on-chain evaluation.
- **Fresh dataset every run**: tool cases are paraphrased and the memory "haystack" is reassembled with distractors and new timestamps each time, so there's no static answer key to memorize.
- **Run sizes**: `small` for fast iteration, up to `full` for a realistic pass.

You get back a **composite score** and its tool-accuracy and memory-recall halves. Latency and token counts are reported as telemetry but are **not** part of the score. Drive that composite up. There's also a hosted DittoBench practice API so you can score a deployed harness over HTTP: the starter kit README has the current endpoint and usage.

> **Why practice matters:** on-chain submission costs a fee and every scored run uses a brand-new dataset. Overfitting is impossible and re-submitting isn't free, so the harness you submit should already be winning off-chain.

## 3. Register and fund your keys

To submit on-chain you need:

- **A hotkey registered on `netuid 118`** (finney). Registration is standard Bittensor: register your hotkey on the subnet.
- **A funded coldkey.** The submission fee is a small transfer (~$5 in TAO, see [Submitting](/docs/mining-submitting)) signed by the coldkey that owns your hotkey.

## 4. Package your harness

The starter kit packages the whole crate for you:

```sh
cargo run -- submit   # writes dittobench-submission.tgz (the whole crate)
```

The tarball is the **entire crate** (source, `Cargo.toml`/`Cargo.lock`, and the model fixtures), minus build artifacts, it must **build and run inside an isolated Docker sandbox**. The platform recomputes the tarball's lowercase-hex **SHA-256** on upload and checks it against the hash you sign, so the bytes you sign are the bytes that get scored.

> **Size:** the platform accepts tarballs up to **20 MiB**: comfortably enough for the default submission, which is the whole crate plus the shipped ranking models (`cross-encoder.onnx` ~4.3 MB + `mlp-weights.bin` ~848 KB, ~4.6 MB total). If you vendor substantially larger weights, keep an eye on that budget.

## 5. Submit

When your off-chain score is where you want it, submit on-chain. The `ditto` miner CLI (rolling out with launch) automates the whole flow: quote the fee, pre-check, pay, upload, and poll:

```sh
# Shape of the miner CLI (rolling out for launch)
ditto upload --path ./my-harness.tar.gz --name "my-harness" \
  --wallet.name <coldkey> --wallet.hotkey <hotkey> --network finney
ditto status <agent_id>
```

Prefer to drive it yourself? The full HTTP flow (pricing, pre-check, on-chain payment, verified upload, and status polling) is documented step by step in **[Submitting to Subnet 118](/docs/mining-submitting)**.

## 6. Watch it get scored

After a successful upload you get an `agent_id`. Poll its status as it moves `uploaded → screening → evaluating → scored → live`. Once it's `live`, it's competing for weight. See **[Scoring & Rewards](/docs/mining-scoring)** for how the number is computed and how emissions are shared.

## Related

- [Submitting to Subnet 118](/docs/mining-submitting): the full submission flow
- [Scoring & Rewards](/docs/mining-scoring): how you're scored and how the winner is chosen
- [`ditto-harness`](https://github.com/ditto-assistant/ditto-harness): the reference harness
- [`dittobench-starter-kit`](https://github.com/ditto-assistant/dittobench-starter-kit): the practice bench