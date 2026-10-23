# Refill selection and wording fixes, medium run (2026-10-23)

## Selection at the same size (offline, `lab/eval_rank.py`)

Tuned on seeds 201-202 salt 5, confirmed on unseen seeds 101-103 salt 7. "complete" = every needed
record in the packet.

| lane | variant | complete (dev / test) | recall (test) | tokens median (test) |
|---|---|---|---|---|
| action | Hades | 96.0 / 89.8 | 0.934 | 5,290 |
| action | swap 12 into Hades's size | 98.7 / 93.5 | 0.958 | 5,258 |
| action | **refill Hades's size from the fused order** | 97.3 / **96.3** | **0.974** | 5,276 |
| action | refill at 12k chars | 94.7 / 93.5 | 0.965 | 2,990 |
| records | Hades | 92.4 / 92.0 | 0.958 | 3,152 |
| records | **refill Hades's size** | 93.0 / **93.3** | **0.966** | 3,152 |

Fusion: reciprocal rank (k=60, depth 80) of the retriever order, meaning order, full-text (bm25, half
weight) and Hades's own packet order. Shipped as `HARNESS_SELECT=refill`.

## Medium run, seed 4242 (same dataset as the Hades run)

| run | composite | tool | memory | prompt tokens | calls |
|---|---|---|---|---|---|
| Hades v6 | 0.862 ± 0.029 | 0.860 | 0.875 | 5.30M | 708 |
| ours e78bab4 | 0.838 ± 0.031 | 0.839 | 0.847 | 5.76M | 729 |
| ours 1da3d1d (refill + wording fixes) | 0.858 ± 0.030 | 0.846 | 0.879 | 5.80M | 777 |

Fixed by the targeted changes (0 -> 1 against both earlier runs): status-current, status-disagree,
world_memory_update ("handoff is Thursday"), set_tool_prefs, memory_save_not_search, three
v13-personal-program (order vote), injection-data-inside-envelope (hyphen fold), negation_web
(NONE guard). Still failing: settings ("system"), absence-false-premise, research-then-email,
schedules count, capability how-to, calendar title ("vet visit for the cat").

New losses against our previous run, traced: one caused by us (world-story-order: the 8,000-token
timeline cap cut a note the answer needed; reverted to Hades's 16,000), six with the same lane and
records where the model chose differently (stale handle answered, a decline that quoted the invoice
amount, a search without a link, a clarification without the note's words, an un-looked-up tool
question, an injection case where the drafts split).

Tokens: refill keeps packet size; the +9% comes from (1) the meaning router sending more questions to
the records lane (about 8 calls each against 3-4 in the action lane) and (2) search passes 109 -> 143
calls, because refill could bring in 7,000+ character case-file records, which switch on the
long-record search passes. Refill now admits new records only under 7,000 characters.

Run-to-run noise on one image is about 0.03 composite on medium; a decision between images needs full
runs (stderr about 0.017) or repeated mediums.
