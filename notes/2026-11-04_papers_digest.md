# 2026-11-04 — 22 papers on agent harnesses, gpt-oss and memory: what applies to horizon

Every paper was read in full text, one by one: arXiv HTML where it existed, the PDF otherwise. Each was judged against
horizon's setting:
- gpt-oss-20b is fixed (no training);
- bench 16 has 50 tool cases and 300 memory cases;
- the cost factor is 1.0 at ≤ $1 a run and 0.6 at $2, and we are at $1.52;
- the rules: the model makes every decision; the host may retrieve, route, annotate and choose tools.

The figures below are the papers' own. Several papers have internal inconsistencies, noted where they matter.

Correction to the brief the readers were given: about 9 calls per question applies only to the full records path,
76 of 175 datagen cases in run 20261104T154802Z. The run average is 5.9 calls per datagen case.

## Verification pass (re-read in my own session from the arXiv HTML, 2026-11-04 evening)

The claims the top approaches rest on, checked against each paper's text:

| Claim in this digest | Verdict | What the text actually says |
|---|---|---|
| Grow the Harness: gpt-oss-20b, 76–92% fewer calls, equal accuracy | **holds, with limits** | gpt-oss-20b (Groq, medium effort, temperature 1.0). BrowseComp-Plus: grown 39.3±12.6% at 6.0 calls / $0.52 vs tool-calling 40.0±11.7% at 24.8 calls / $2.03. WebArena: 44.7% at 1.8 calls vs 12.7% at 22.3. But the paper **does not say which steps became code**. Output tokens went **up** (14.3k vs 8.3k). Optimiser cost is excluded, and the ablations are single runs. |
| Engram answers in one call over a lean context | **overstated** | The answerer is doubao-seed-2.0-pro, a strong model, not ~20B. The read-time call count is not stated (latency is "dominated by" the answer call; decomposition may add calls). The headline run used a write-time LLM fact extractor. Lean 83.6% vs full 73.2% is significant (McNemar p < 1e-6). The facts-only ablation was not run, and there are no per-type full-context numbers. The answer prompt ("dig for the answer first", one ANSWER line, abstain "I don't know") is confirmed. |
| SimpleMem: "without absolute times, temporal −57%" | **misattributed** | The −56.7% temporal (F1, LoCoMo, GPT-4.1-mini) is for removing the **whole** semantic-compression step (timestamps and coreference together), not timestamps alone. Its LongMemEval full-context baseline (39.6) is unusually low, so treat the gains with care. Read time is about 2 calls (planner + answer), inferred, not stated. |
| Model card effort table and hallucination numbers | **exact** | All figures match Table 3 and Table 9. The card gives no temperature advice. Effort is set by "Reasoning: low/medium/high" in the system prompt, and past reasoning is dropped in multi-turn. |
| EffGen complexity gate | **holds** | τ = 7.0 over five weighted factors. Below it, a single-agent ReAct loop; above it, decomposition. Removing routing costs 3.6 points at 1.5B, 6.2 at 7B and 7.9 at 32B. Temperature 0.1. |
| EffGen gpt-oss-20b numbers (LoCoMo 21.4 → 10.3 under LangChain) | **unverified** | They are in Appendix U.1 / Table 51, which the HTML omits; a reader took them from the PDF. LangChain's memory losses are explained as truncating old context, not piling it up. |
| Better Harnesses: "no sub-agent change ever helped", used against drafts | **weak evidence** | "we do not see successful harness adaptation of creating sub-agents" means sub-agents, not drafts. The paper does not study drafts or self-consistency. Harness cost rose for gemma ($0.043 → $0.071) and fell for the other two models. |

What stands after the check:
1. The case for one deciding call rests mainly on **our own live data**: Hades v24 and v26 answer these questions in ~1 call at accuracy 1.00. *Grow the Harness* backs it as the one paper on gpt-oss-20b. Engram and SimpleMem are supporting evidence on stronger models. **No paper tests whether our 3 drafts or the follow-up question help gpt-oss-20b, in either direction**, so the lean A/B on the same seed is the real test.
2. Our packet is already lean (≤ 24k chars, ~6k tokens, comparable to Engram's 9.6k), so the "lean context beats full history" lesson is mostly already applied. Our gap is **calls**, not context size.
3. Expect completion tokens per call to rise when calls fall. Grow the Harness shows this on gpt-oss-20b. At $0.15/M it is a small cost against prompt savings, but measure it.
4. Supersession and alias notes (approaches 2–3) are supported as *ideas* by Engram and SimpleMem. Their measured effect on a ~20B answerer is unknown, so A/B them.

## Ranked approaches for horizon

| # | Approach | Sources | Problem | Est. value |
|---|---|---|---|---|
| 1 | **Collapse the records path to one deciding call, with code doing the recurring work.** Drop the timeline pass, follow-up question and multi-pass search; a second call runs only when code sees a trigger (no evidence cited, conflicting amounts, a decline). | Grow the Harness (gpt-oss-20b: 76–92% fewer calls, 74–99% lower cost, equal or better accuracy); Engram (one call over a ~9.6k lean context, 83.6% vs 73.2% full history); Better Harnesses (no sub-agent change ever helped); EffGen (gate the expensive steps on complexity); Hades v24/v26 live (~1 call, 2–4 s) | calls, completion tokens, cost | highest: $1.52 toward ≤ $1, factor 0.79 toward ~1.0 |
| 2 | **Deterministic supersession and timeline notes**, advisory, with records kept and shown in date order. A (subject, attribute) slot table plus embedding same-attribute links gives "record #12 (Mar 3) superseded by #31 (May 9)". For as-of questions, mark the records dated after the asked date rather than dropping them. | Engram (bi-temporal facts; supersedes chain, never delete); SimpleMem (absolute timestamps: temporal −57% without them); RecMem (raw records are essential: −29 points without them) | updates, stale values, revert-to-previous, point-in-time, arithmetic over changed amounts | high: keeps accuracy when the drafts are removed |
| 3 | **An ingest-time alias and date index** (host, no LLM). Full name ↔ nickname ↔ initials across all records, relative dates made absolute. One host retrieval pass (BM25 + dense + date window, unioned) replaces up to 5 model search passes. | SimpleMem (entity normalisation, multi-view retrieval); RecMem (same-topic cluster note); our hard pack (nickname-only questions miss the full-name record) | multi-item lists, multi-hop, nickname questions, calls | high |
| 4 | **Engram-style answer format in that single call.** List dated evidence one per line, show 1–2 lines of working for counting, sums, orders and durations, newest dated value for current state, "dig first, abstain last", and for a decline name what the records do hold; then one ANSWER line. | Engram prompt; model card (gpt-oss rarely abstains: SimpleQA hallucination 0.914, so state the decline option plainly) | absence, arithmetic, updates | high, and cheap |
| 5 | **Set reasoning effort per call:** low for retrieval-like calls, medium only for deciding arithmetic or list questions, never high. | Model card (MMLU 80.4/84.0/85.3, GPQA 56.8/66.0/71.5 by low/medium/high; τ-Airline high < medium); Grow the Harness (gpt-oss-20b ~2.4k output tokens a call at medium) | completion tokens | medium |
| 6 | **Retrieval discipline:** a hard evidence cap, de-duplication, later passes labelled "additional", never overriding. | EffGen (piling context on gpt-oss-20b roughly halved LoCoMo, 21.4 → 10.3; small models drop right answers after loosely related text) | memory accuracy, prompt tokens | medium |
| 7 | **Per-stage instructions:** our own system text assembled from tagged chunks by question type and stage, with a small always-on core, instead of the whole block on every call. Flat prompt pricing means per-call variation costs nothing; check the I4 ruling. | ITR (dynamic system instructions) | prompt tokens | medium |
| 8 | **Tool cases:** a short instruction block (stop after the completing call, check required parameters); validate a call against the catalog and re-ask once on an unknown tool, bad JSON or a call mixed with an answer; try temperature 0 or low. Keep our deterministic selector. | Effectiveness/Efficiency (prompt content +13–15 pts on a 4B model for < 220 tokens); Harmony (recover-and-retry); TinyAgent (95%-recall retrievers lose accuracy against offering all; ours is 100%); EffGen (70–87% of tool errors recovered by retry) | tool accuracy | low to medium (50 cases) |
| 9 | **Regression gates on calls and tokens per question**, not only accuracy; compare A/B per case, not by aggregate. | Don't Blame the LLM (+70% tokens across releases at flat quality; failures cost 2.7×); Beyond Token Savings (aggregates hide 6–14 tasks of turnover) | keeps cost from creeping back | method |
| 10 | **A failure-window harness optimiser** with a held-out gate and rollback, success-first; raw trace.jsonl as input and edits only to functions in failing traces. | Grow the Harness (without the gate it regressed 30% → 16%); Better Harnesses (GEPA-style; raw JSON traces beat summaries) | process for 1–3 | method |

Not worth adopting:
- Fine-tuning, RL or distillation (TinyAgent planner, Harness-Aware Distillation, RL halves): the model is fixed.
- Rewriting tool descriptions (EASYTOOL) or lazy schema summaries and gateway meta-tools (Tool Attention, the MCP
  study): tools must pass as supplied, and these add turns.
- Embedding retrieval to replace our selector: lower recall.
- LLM-written memory units or episodes that replace records: a rule conflict, and RecMem shows a collapse without raw
  turns.
- Write-time LLM consolidation: priced calls, no update or temporal gain.
- A larger-model fallback (the small-model survey): there is no larger model.

Already in horizon: the `calculate` tool in the records lane (the arithmetic-tool idea, M11) and the deterministic
tool selector (v16_atlas/toolselect.py).

## Paper records

### Harness design

1. **Better Harnesses, Smaller Models (2607.08938)** — medium-high.
   - Idea: move difficulty that recurs across tasks into the harness, found by a meta-agent reading raw failure
     trajectories (GEPA-style search, validation-gated).
   - Winning edits: cut the tool set (40+ → 7), wrap multi-step patterns into one tool, a numbered-procedure system
     prompt, domain conventions in the prompt, an anti-loop hook. No sub-agent change ever helped.
   - Numbers: gemma-4-26b 31.4% → 80.2% (gemini-3.1-pro 89.7%) at about 4% of its cost.
   - Repetitive tasks gain most (ρ = −0.96 between diversity and optimised accuracy), which favours the 125
     official-generator questions.
2. **From QA to Task Completion, survey (2606.20683)** — low.
   - A six-part harness taxonomy, and value × success under cost limits.
   - Same model across harnesses: median spread 13.6 points on Terminal-Bench 2.0. A ~100-line mini-SWE-agent
     (76.8%) nearly matches OpenHands (77.6%).
   - Framing only.
3. **Grow the Harness, Not the Context (2609.26760)** — high; tested on **gpt-oss-20b**.
   - Idea: an optimiser grows harness code from failure traces. Control (parsing, validation, state, query
     refinement, stopping) becomes code; the model does semantic judgment and the answer.
   - Method: failure window K = 8, ≤ 5 repairs per task, ≤ 10 trace-scoped edits per step, a held-out gate with
     rollback, success-first selection.
   - Numbers: BrowseComp-Plus 39.3% at 6.0 calls ($0.52) vs 40.0% at 24.8 calls ($2.03); WebArena-Verified 44.7%
     at 1.8 calls vs 12.7% at 22.3. gpt-oss-20b produced ~14.3k output tokens a task (~2.4k a call).
4. **Harness-Aware Distillation (2610.02858)** — low.
   - The training method is out of reach.
   - Harness lessons: short state-style lines in the last user turn, fired on ≤ 5% of steps, informing and never
     blocking (blocking lowered success to 55.2). State tracking matters more than behaviour monitoring.
5. **Don't Blame the LLM (2607.03691)** — medium (cost).
   - 35 releases of one harness on a fixed model: resolve rate flat (23–39%), tokens +70% (391k → 668k).
   - Turns and tokens correlate at ρ = 0.94. Unresolved tasks cost 2.7× tokens and 1.8× tool calls.
   - Formatting and prompt bloat raised tokens; fixing compression (−26%) and deleting dead modules (−13%) cut them.
   - Use: gate on cost per question.
6. **Three Roles, One Model (2604.11465)** — low-medium.
   - Summariser, agent and corrector, each with its own narrow context, on Qwen3-8B.
   - The corrector (proposed code, API docs, last error) gives most of the gain: 5.4% → 8.9% on AppWorld.
   - Possible use: a corrector only after a tool call fails schema validation.

### gpt-oss and small models

7. **In harmony with gpt-oss (2604.00362)** — medium.
   - Low third-party scores come from the harness (missing trained-on tools, Chat Completions conversion). Native
     harmony reproduces the published numbers (SWE-Verified high 60.4 vs 60.7).
   - The model has strong priors for tools it never saw (`apply_patch` called 860 times), and prompt words steer
     tool choice.
   - Use: recover-and-retry on malformed calls; memory-search tool names that mirror its built-in browsing tool.
8. **gpt-oss model card (2508.10925)** — high.
   - 20b: 3.6B active parameters, 131k context, harmony channels (analysis / commentary / final), three effort
     levels.
   - Effort table (low / medium / high): AIME25 no tools 37.1/72.1/91.7, with tools 57.5/90.4/98.7; GPQA
     56.8/66.0/71.5; MMLU 80.4/84.0/85.3; τ-Retail 35.0/47.3/54.8; τ-Airline 32.0/42.6/38.0.
   - Hallucination: SimpleQA accuracy 0.067 at 0.914 hallucination; PersonQA 0.155 / 0.532. It rarely abstains.
   - Message priority: system > developer > user. Drop past reasoning in multi-turn.
9. **GPT-OSS-20B deployment analysis (2508.16700)** — none. Throughput, memory and energy only: "We do not evaluate
   accuracy".
10. **Is GPT-OSS Good? (2508.12461)** — low; unreliable. Text and tables contradict each other, and the setup used a
    2,000-token output cap and no effort setting. One usable signal: weak numerical precision.
11. **EffGen (2602.00887)** — high.
    - Idea: an agent framework for small models. Prompts shortened 57%, a 0–10 complexity gate (threshold 7)
      before the multi-step machinery, decomposition, and three-tier memory.
    - gpt-oss-20b (Table 51): average 56.75 raw, 56.01 LangChain, 57.68 AutoGen, 67.82 EffGen.
    - LoCoMo 21.4 raw vs 10.3 with LangChain; LongMemEval 28.9 vs 16.6. Absolute scores are low (2,048-token cap),
      so read the gaps.
    - 70–87% of tool errors were recovered by retry. Small models drop right answers after loosely related
      retrieved text.
12. **Small Language Models for Agentic Systems, survey (2510.03847)** — low.
    - Small models by default with a larger fallback, schema-first output, validators, confidence escalation.
    - No measurements of its own; the ablation table says "fill with your measurements".
    - Transferable: temperature 0 for structured tool output; agreement between samples as a stop signal.

### Tools

13. **TinyAgent (EMNLP 2024 demo)** — low.
    - Fine-tuned 1.1B and 7B LLMCompiler planners with a DeBERTa tool classifier (16 tools, ~4 kept).
    - Classifier recall 0.998: 84.95% success. Basic embedding RAG at 0.949 recall (78.50%) did worse than all
      tools (83.09%).
    - Supports our 100%-recall selector over any embedding retriever. Parallel tool calls in one turn may save
      turns.
14. **Dynamic System Instructions and Tool Exposure, ITR (2602.17046)** — medium (our own instructions).
    - Retrieves system-prompt chunks (200–600 tokens) and tools per step, under a token budget.
    - 30k → 1.5k tokens a step, tool-correct 62% → 82%. As tools grow 8 → 120, all-tools falls 74% → 45% and ITR
      84% → 76%.
    - Small task sets, undisclosed model. Use: chunk our own prompts by question type and stage.
15. **Tool Attention (2604.21816)** — low.
    - A MiniLM gate (θ 0.28, top-10) with ~60-token summaries for all tools and full schemas only for the active set.
    - Only token counts are measured (47.3k → 2.4k); success figures are projected. Needs rewritten summaries
      (forbidden).
16. **EASYTOOL (NAACL 2025)** — none for the core method.
    - LLM-rewritten concise tool instructions: tokens per tool −70% / −97%; ToolBench success for ChatGPT 15.0% →
      52.8%, Llama-3.1-8B 5.5% → 48.5%.
    - Rewriting descriptions is forbidden. At most, contrast lines for commonly confused first-party tools in our own
      prompt, if traces show confusion.
17. **MCP vs CLI across seven scaffoldings (2608.08654)** — medium-high as diagnosis.
    - The scaffolding's per-request resend dominates: 14.7k to 289k input tokens per run (20×), with output tokens
      flat.
    - Catalogue cost multiplies with turns (139× between scaffoldings for one model). Failed runs cost about 2×.
    - Removing a route changes behaviour; instructions don't.
18. **Effectiveness and Efficiency of Agentic Tool-calling and RL (2606.00135)** — medium.
    - A better system prompt took Qwen3-4B BFCL multi-turn from 22.9 to 37.5 (two notes alone gave 36.0); content,
      not length.
    - Native role-separated chat beats packed history by 6–8 points; keeping reasoning across steps gives +2–5.
    - The RL half is not applicable.

### Memory and context

19. **SimpleMem (2601.02553)** — medium.
    - Write time: atomic, coreference-resolved, absolute-timestamped memory units (20-turn windows, one LLM call
      each).
    - Read time: one planner call (keywords, time limits, semantic query) and parallel dense, BM25 and SQL
      retrieval, then one answer call of ~530 tokens.
    - Numbers: LongMemEval-S (GPT-4.1-mini) 76.9 vs 39.6 for full context; temporal 83.5, knowledge-update 79.5,
      multi-session 60.9.
    - Without absolute times, temporal falls 57%. Small models gain most (Qwen3-8B LoCoMo 33.5 vs 11.2).
    - Use: host-side dates and entities only (keep the records).
20. **Engram, "Less Context, More Accuracy" (2606.09900)** — high.
    - Data model: dated raw episodes plus a bi-temporal fact graph (valid and transaction times, a `supersedes`
      pointer, provenance). Supersession checks cheap things first (slot match → embedding → subsumption → LLM only
      if ambiguous).
    - Read: four channels fused by weighted RRF, an as-of filter, an abstention gate, a lean context of ~9.6k tokens.
      Answered in one call.
    - Numbers: LongMemEval-S 83.6% vs 73.2% for full history; knowledge-update 87.5, abstention 86.7, temporal
      81.1, multi-session 79.3.
    - The answer prompt is the template for approach 4.
    - Strong answerer model; single run.
21. **RecMem (2605.16045)** — low-medium.
    - Verbatim turns and embeddings; an LLM consolidates only when a topic recurs (θ_sim 0.6–0.7, θ_count 4–5).
    - Numbers: LongMemEval 76.8% at 5.9k tokens vs 66.2% at 112k for full context; worse on knowledge-update.
    - Without raw turns LoCoMo drops 81.1 → 51.9. Use: a host-side cluster note and a "don't double-count" line.
22. **Beyond Token Savings (2609.32961)** — low.
    - 65 compression policies on coding agents: token savings don't predict accuracy or cost.
    - Tool-result clearing holds accuracy at 0.71× cost; free-form summaries lose 11 points; summary calls take
      28–46% of wall time.
    - Use: count calls, compress less, compare per case.

## Fit with the evidence we already have

- Hades v24 and v26 answer absence, point-in-time and trip questions in 2–4 s (about one call). Our full records
  path makes 9.2 calls a case: 68% of calls and 72% of prompt tokens in our run. That is the same finding as Grow
  the Harness and Engram: the accuracy machinery (3 drafts at 0.7, follow-up question, timeline, search passes) costs
  far more than it returns.
- The follow-up question leaks distractors on list questions (hard pack) and fires on 39% of memory questions with
  2 extra calls. No paper supports it.
- None of the papers tests drafts or self-consistency on gpt-oss-20b; our three drafts at 0.7 have no support in
  this literature, so measure them.
- Next step after Hades v24's source (22:18 UTC): compare its one-call records design with approaches 1–4, then a
  settings-and-code A/B on the same seed as run 20261104T154802Z.
