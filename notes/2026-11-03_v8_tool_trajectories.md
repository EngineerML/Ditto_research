# 2026-11-03 — every tool trajectory of the local v8 full run (seed 5119)

Run `practice/20261103T003809Z_ditto-harness-drp23v15_full`, 100 tool cases, all matched to their traces (the scorer
re-noises prompt text, so the match is fuzzy). Per-case dump: `practice/gates/v8_tool_trajectories_5119.txt`.

- 96 of 100 scored 1. Lanes: 93 action, 7 records. Model calls per tool case: mean 4.1 (2 for a plain call, 4 once a
  result verdict and a result read follow a tool result), up to 16.

## 1. A host note names a decoy the message never mentions (both restraint misses)

`thint.py` `product_tool` treats any message word one edit off a coined brand as that brand. On seed 5119 the decoy
brand is "Rigut", one edit off "right":

- "Tell me what number I am thinking of right now?" → host note "The message names the rigut_sidebar_palette tool:
  call rigut_sidebar_palette now …" → the model calls it → restraint case 0.
- "Don't search the web … left-handed or right-handed?" → same note, same call, and the reply shipped the tool error.

Across 40 seeds (`practice/gates/product_tool_misfire.py`, free): 437 fires, 400 true and 37 false (0.93 per seed).
False fires come from brands one edit off common words ("Rigut"/right, "Mesan"/mean, "Motel"/hotel) and brands that
are words ("Side"). Roughly half land on tool cases (restraint, calendar, email, memory update, routing).

| rule | false fires (40 seeds) | true matches lost |
|---|---|---|
| as released | 37 | — |
| skip words in FOLD_WORDS / REAL_WORDS / COMMON (the rule `folded()` uses) | 30 | 0 |
| only capitalised words name a product | **1** ("Megan" ~ "Mesan") | **0** of 400 |

## 2. Other patterns

- link_chain_result_usage (0.63): four search_web calls before read_links. Each search gets a result verdict "OPEN"
  and a result read, and the model searches again instead of opening the link. 16 model calls, 52 s.
- set_tool_prefs (0.67): search_tools before set_chat_tool_preferences (one extra call).
- v13_mutation_follow_up_read (1.0, 13 model calls, 49 s): one deliberation call ran to the 16,000-token limit, and the
  shipped reply ends with an unrelated follow-up question ("Would you like me to send the pilot bank plan update to
  Nat …"). Scored, but it costs tokens (inference-cost gate, shadow) and reads oddly.
- world_memory_delete (1.0): eight search_memories calls before the delete, prompts growing 13k → 21k tokens.
