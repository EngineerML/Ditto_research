# Bench-15 tool-case atlas

Corpus: 200 full v15 seeds, 20,000 tool cases. **All prompt counts and examples use the served text** (`.cache/served/v15_s<seed>_served.json`), joined by case id to `.cache/datasets/v15_s*_salt0_full.json` for expected tools, args and the catalog. Only 6,188/20,000 dataset-file prompts equal the served prompt, because the files carry an extra typo pass that is never served (§1 step 7). Paths are relative to `repos/ditto-subnet/research/dittobench-datagen`; scorer = `services/dittobench-api/internal/scorer`. Counts are exact unless marked *est.* Scripts: `/tmp/atlas_tool/`. Per-category detail (frame distributions, arg values, surface rates) is in `tool_families.json`.

## 1. How a v15 tool set is assembled

`gen/tools.go:25` → `datagen/datagen.go:2120`. Profile `full` = 100 tool cases (`gen/gen.go:146`). Passes, in order:

1. **Family mix** (`datagen/v13.go:131`, own FNV RNG `datagen.go:1131`). 46 source families (`datagen.go:1985`). Each non-optional family gets one floor slot; 55 slots are weighted draws (stale_context_web 8, job_chain 7, link/recovery chains 6, web_recovery 5, `_not_`/route/multi 2, set_effort 2 optional, else 1). Order shuffled.
2. **Render.** Grammar per case from a per-seed bank (`persona.SeedBank` keeps ~2/3 of each non-root symbol; roots never thinned). `wrap` families add lead-ins/trailers (`datagen.go:621`). v8 overrides retarget recipes/automations/workflows to `create_workflow`, `list_schedules`, `list_workflows`+`run_workflow` (`datagen.go:2008`).
3. **World conversion** (`datagen.go:1484`). The 7 retired families always convert; duplicates convert up to ~40 world actions (min 34). Kinds: contact-email (×2), delete, update, theme, business-workflow, link-chain, agent-job. One case becomes the **carrier** of the whole world (332–349 prerequisite pairs).
4. **State routes** (`datagen.go:1346`). Each agent-job world case becomes one of 5 routes: job / create / run workflow (`v10_state_dependent_routing`), calendar, or email.
5. **v13 tool bench** (`datagen/v13.go:254`). recipe_apply becomes cadence-named; world_theme is capped at 3; adds 6 discovery, 10 decoy-correct, 4 coined-fixture cases (ordinary duplicates are taken first).
6. **v13 semantics** (`v13_tool_semantics.go:163`). 16 restraint cases (4 triplets + 2 pairs, family drawn with replacement, 2:1 or 1:2 ask:act). Memory reads are capped at 8, effect-graded on planted facts; 2 become follow-up reads. Update/delete prompts get cue-inverted grammars.
7. **Surface pass: dataset files only.** `gen/v13_surface.go:98` adds typos to 70% of prompts in the hashed artifact (1 edit per 12 words, salt-keyed). The live scorer serves `GenerateToolsForVersion` output directly (`services/dittobench-api/cmd/dittobench-api/main.go:1542-1571`) at salt 0, so **served prompts are clean generator text**. The only deliberate misspellings are appearance values: about 8.2% of tool prompts (discovery_* and world_theme, via `misspellAliasV13`, `datagen.go:1767`). Prerequisite story pairs carry generation-time typos.
8. **Serving.** IDs become UUIDs. Order is an HMAC permutation under a validator key (`gen/projection.go:399`), then repaired so twins are ≥20 apart and follow-ups ≥40 after their mutation (`gen/v13_tool_order.go:24`). **Dataset JSON order ≠ served order.**

**Per-run mix** (means over 200 runs; every run has exactly 100):

| bucket | /run |
|---|---|
| restraint groups (6 families) | 16.0 fixed |
| world_* (6 families) | 17.8 (each family 1–8) |
| state-dependent (3) | 13.7 (3–20) |
| decoy-correct (23 shapes) | 10.0 |
| discovery accent+font | 6.0 |
| coined-fixture "unexpected" | 4.0 |
| effect-graded memory reads + 2 follow-ups | 4.5 + 2 |
| ordinary families present every run (15) | 15 |
| ordinary families present ~55–72% of runs (18) | ~11 |

**Memory waves.** The validator seeds all tool prerequisites first (~369 pairs/run, 358–381): the world carrier plus each case's local record (restraint notes, planted facts, state records, stale notes, accountant record). They share one user graph, hence the "planning context" scope (H10). Tool cases run next. The 6 memory waves (335–367 pairs, incl. a `colleague` isolation wave) come after and share no pair IDs with tool prerequisites (checked on 1 seed). World families resolve against carrier facts (aliases, nicknames, current/previous email, disposable notes, scratchpads, preferences). State and restraint cases read their own record.

## 2. Families

`runs` = runs of 200 containing the family; `F` = root frames. Grading: **S** = strict single (0.4 name-F1 + 0.4 args + 0.2 trajectory, extra calls penalised ×2; one stray call → 0.667), **C** = ordered chain (order credit multiplies score), **RU** = result-usage gate (×1 needle / ×0.1 neither / ×0 decoy figure), **Z** = fuzzy (max 15, extras free, every capability + outcome arg required else 0), **E** = effect read (any non-memory call = 0; answer must carry planted value), **R** = restraint (ask: no action, text-graded). Details: JSON `grading.rule`.

### 2a. Ordinary single-tool families (max 1, allow_extra false, S)

| category | src (datagen/) | F | representative frame | expected | runs, mean | rare/odd |
|---|---|---|---|---|---|---|
| web_search | datagen.go:211, grammars_v13.go:51 | 6 | `#searchverb# %s.` / `What are people saying about %s #now#?` | search_web | 114, .57 | verbs: Search the web for / Look up / Google / Check online for; topics come from the v5 pool |
| route_web_not_memory | :278, g13:135 | 6 | `Remind me what the #latest# #news# on %s is.` / `Remember to tell me what's #happening# with %s #today#.` | search_web | 116, .58 | 89/116 use remind/recall/remember/do you know |
| stale_context_web | :1255, g13:536 | 6 | `My saved notes on %s are #stale# — #fetch# what's #current#.` / `Forget what I said about %s before…` | search_web | 200, 1.0 | carries a stored stale note; 200/200 anchor on notes/told/forget/ignore/said |
| image_create | :228, g13:80 | 6 | `#genverb# an image of %s.` / `Draw me %s.` | create_image | 124, .62 | |
| image_edit_not_create | :302, grammars.go:57 (wrap) | 5 | `Take #imgref# and #directchange#.` | edit_image | 142, .71 | 35/142 contain make/give/add |
| artifacts_create | :236, g13:93 | 6 | `Make %s I can #preview#.` | artifacts | 200, 1.0 | "pomodoro timer", "budgeting spreadsheet mockup" (136/200 look like another tool) |
| agent_job | :244, g13:108 | 6 | `Have a worker %s — #inbg#.` | execute_agent_job | 109, .55 | tasks say "cron job", "script" |
| agent_run_not_read | :287, g13:150 | 6 | `Please actually %s, #notjust#.` | execute_agent_job | 119, .59 | 43 negate "don't just tell me how" |
| agent_read_not_run | :296, grammars.go:20 (wrap) | 7 | `Did #onejob# #finish# yet?` | list_agent_jobs | 200, 1.0 | lead-ins 113/200 |
| workflow_not_job / agent_workflow / recipe_create / automation_not_job | :310/:362/:430/:418 → create_workflow (:2027–:2054) | 5 each | `I want %s as a #reusable# workflow, not a one-off…` / `Make a reusable workflow called %s.` / `Put my news digest on a #timer#: %s.` | create_workflow (no args) | ~.55 each | "not a one-off", "in parallel"; schedule text inside a create |
| automation_list | :426→list_schedules, g13:300 (wrap) | 6 | `Remind me which #autoruns# are coming up.` | list_schedules | 200, 1.0 | "Remind me" 39 |
| capability_discovery | :448, grammars.go:136 (wrap) | 6 | `Is there a way to #settingtask#?` (turn on dark mode / adjust the chat font) | discover_capabilities | 200, 1.0 | names a setting it must not set (97/200) |
| feedback | :370, g13:233 | 6 | `Report to the devs that %s.` | file_feedback_for_team | 200, 1.0 | fillers name other tools ("the image tool keeps timing out", "love the new memory search"): 200/200 |
| set_tool_prefs | :407, g13:278 | 6 | `Going forward, %s — #savepref#.` | set_chat_tool_preferences | 200, 1.0 | "disable web search", "enable image tools" (200/200) |
| settings | :252; intents g13:596 | 6 | `Light or dark — just #follow# my system setting.` / `#go# dark for the whole app.` | set_theme {theme: system 102 \| dark 98} | 200, 1.0 | only system/dark ever; the verbatim grammar (g13:249) is dead |
| set_effort | :399; intents g13:604 | 6 | `#deep# — I'd rather wait than get a shallow answer.` | set_reasoning_effort {high 65 \| medium 72} | 137, .69 | never "low" here |
| memory_save_not_search | :454, g13:338 | 6 | `Just so you know, %s — #saveask#.` | save_memory | 200, 1.0 | |
| calendar_create | :478, g13:373 | 6 | `#bookverb# %s for me.` | calendar_create_event (no args) | 128, .64 | |
| calendar_search | :486, g13:385 | 6 | `Do I have %s #booked#?` | calendar_search_events | 137, .69 | the filler is always a **web topic** ("quantum error correction") |
| code_compute | :1150 (override :2014) | 2 | `#lead# take #a#, #b#, and #c#, then give me their sum…` | run_code | 123, .61 | |
| code_compute_not_agent_job | :1165 | 4 | `No need to spin up a whole project… just compute #a# times #b# minus #c#` | run_code | 126, .63 | negation 126/126 |
| tool_discovery | :1180 | 4 | `What tool would you use to #cap#? Search for it first.` | search_tools | 200, 1.0 | 5 caps shared with tool_registry |

### 2b. Multi-hop and result-usage (allow_extra false)

| category | src | F | frame | expected / grading | runs, mean | odd |
|---|---|---|---|---|---|---|
| multi_web_read | :521, g13:430 | 5 | `Search for %s and #summ# the first source.` | search_web→read_links, C | 114, .57 | |
| parallel_web_image | :532, g13:442 | 5 | `Two things: find the latest on %s and create an image of it.` | search_web+create_image, unordered | 133, .67 | "Two things"/"I want both" |
| multi_image_edit | :556, g13:477 | 5 | `Render %s and afterwards #tweak# it.` | create_image→edit_image, C | 126, .63 | the grammar emits "tighten the crop it", "brighten it it" |
| web_result_usage | :571, g13:488 | 5 | `Check online: what precise #figure# is being reported for %s?` | search_web, S+RU | 200, 1.0 | %s = "the <OrgStem> <noun>" |
| multi_web_result_usage | :579, g13:500 | 5 | `Find a page about %s, read it, and give me the precise number.` | search_web→read_links, C+RU | 200, 1.0 | the needle is only in read_links |
| link_chain_result_usage | :1263, g13:549 | 4 | `…read the linked page (not just the snippet)…` | same, read_links gated on the served URL | 200, 1.0 | |
| web_recovery_result_usage | :607, g13:524 | 4 | `#searchverb# %s and #report# the exact #figure# — #retry#.` | search_web, allow_extra true, first call errors | 200, 1.0 | |
| schedules_ / tool_registry_ / sandbox_ / agent_jobs_result_usage | v13.go:622 (prompts :600–:615) | 3 each | `Look at what's on a timer for me: the workflow scheduled %s…` / `Execute %s in the in-process sandbox…` / `How many items did my %s job get through?` | list_schedules / search_tools / run_code / list_agent_jobs, S+RU | ~199 each, 1.0 | %s = cadence / cap / "<Stem> checksum" / "<Stem> export" |
| recipe_apply | :438→v13.go:263 | 3 | `Kick off my workflow that's set for %s — the one already saved.` | list_workflows→run_workflow{name=<coined "Stem noun">}, C | 200, 1.0 | the name exists only in the served list |

### 2c. Decoy-correct, 23 shapes (`decoy_<shape>_result_usage`, `datagen/v13.go:359`, shapes `catalog/v13.go:450–519`)

There are 3 frames per shape, using `%[1]s` = Brand and `%[2]s` = needle subject. For example, wiki: `Check our %[1]s wiki on %[2]s — what precise number does it give?`; chat: `Drop a note in our %[1]s team channel asking about %[2]s…`; timer: `Kick off a %[1]s timer labeled %[2]s…`. Expected `<stem>_<suffix>` with max 1, grading S+RU. There are always 10 per run, cycling over the seed's 3–5 decoys, so a brand is expected 2–4 times per run. Shape presence ranges from address_book 20/200 runs to markets_quote 55/200 (full list in JSON). Every prompt asks for the "exact/precise figure", the same request shape as the web result-usage families.

### 2d. Appearance discovery

| category | src | F | frame | expected | runs, mean | odd |
|---|---|---|---|---|---|---|
| discovery_accent_set | v13.go:504 (prompts :568, near-miss :583) | 4+3 | `Set my accent to %s (or whatever the closest configured option is called)…` / `Make Ditto's accent the %[1]s version of %[2]s, not the plain one.` | discover_capabilities→set_accent_color{color}, Z | 200, 2.72 | 148/544 near-miss ("the green shade of pie" → the partner option) |
| discovery_font_set | same | 4+3 | `Use the %[1]s edition of %[2]s for chat.` | …→set_chat_font{font}, Z | 200, 3.28 | 252/656 near-miss; 132 distinct font values observed |
| world_theme_discover_set | datagen.go:1832, g13:695 | 4 | `Have Ditto use my usual #accent#-ish accent — …not one of the client brand colors.` | discover→set_accent_color{world.Accent}, Z | 200, 2.23 (cap 3) | the misspelled world accent |

### 2e. Memory reads (effect-graded, E, max 2)

memory_lookup (133 runs), memory_subject (141), route_memory_not_web (150), memory_fetch (140), multi_subject_scope (150), entity_lookup_chain (160); 4.5/run combined. **All six use one prompt source**: 8 planted facts × 3 questions (`v13_tool_semantics.go:816`, e.g. "What's my gym locker combination?"); value = 4 digits or `ABC-123`. Their category grammars never reach the wire; the differing expected lists are not graded. `v13_mutation_follow_up_read` (2/run, `:1057/:1088`, 6 frames) asks the post-mutation handoff day or preserved email; naming the stale value also scores 0.

### 2f. World families (Z, carrier-dependent)

| category | src | F | frame | expected (graded args) | runs, mean |
|---|---|---|---|---|---|
| world_contact_research_email_result_usage | datagen.go:1798, g13:652 | 8 | `For #nickname# — my #relation# in #city#, from the #context# — #check# #subject# and #sendto# them.` | search_web + gmail_send{to=current email, body=needle} | 200, 3.35 |
| world_link_chain_result_usage | :1852, g13:715 | 4 | `What's #subject# at now? Open the source page instead of going by the search preview.` | search_web + read_links | 200, 3.26 |
| world_memory_delete | v13_tool_semantics.go:1001 (prompts :790) | 4 | `Update my notes on %[1]s: the temporary email-fix receipt from the %[2]s is done, so drop just that one…` | delete_memory{pair_id}; other pairs of the person are forbidden | 200, 3.29 |
| world_memory_update | :963 (prompts :772) | 5 | `Forget Friday for %[1]q: handoff is %[3]s. Keep that in the handoff scratchpad…` (+"Also, X is the reviewer" in 258/647) | update_memory{pair_id, content claim}; alternative delete+save | 200, 3.23 |
| world_business_workflow | datagen.go:1840, g13:706 | 4 | `Do I already have a workflow for #alias# (the #client# project)? If there isn't one, create it under the formal project name…` | list_workflows + create_workflow{name=formal, steps=reviewer current email}; the other client is forbidden | 200, 2.44 |

### 2g. State-dependent (Z): identical ask, the record decides

| category | src | frames | outcomes (count) |
|---|---|---|---|
| v10_state_dependent_routing | datagen.go:1346; ask g13:748 (2 roots, ~40 surfaces) | `#lead# the dependency-risk review for #alias# #tail#` | execute_agent_job 505 / create_workflow{name} 533 / list_workflows→run_workflow{name} 520; 200 runs, mean 7.8 (3–14) |
| v13_state_dependent_calendar | v13_tool_semantics.go:1134 | 3 (`Make sure the "<alias>" review is on my calendar for <day>.`) | calendar_search_events 279 (create is forbidden) / calendar_create_event 304; mean 2.9 |
| v13_state_dependent_email | :1161 | 3 (`Get back to them on the "<alias>" numbers.`) | gmail_send to the requester (exists) or the planned recipient (absent); mean 3.0 |

### 2h. Restraint groups (R + Z), `v13_tool_semantics.go:584`

| family | ask move | act move | prompt | ask/act |
|---|---|---|---|---|
| effort (:638) | clarify, citing the two stored styles ("quick answers"/"deep dives") | set_reasoning_effort{stored low/med/high} | `For planning context <id>: <lead><verb> <noun><tail><trailer>.` | 263/257 |
| calendar (:663) | clarify when (no date stored) | calendar_create_event{title} | `…stick it onto my schedule…` | 246/277 |
| email (:683) | clarify who, citing the asker nicknames | gmail_send{to=stored email} | `…shoot them my update on <alias>…` | 265/266 |
| negation_web (:709) | answer from knowledge | search_web | negated vs affirmed lead + one of 6 GK questions | 286/296 |
| abstention_web (:719) | answer honestly, no tool | search_web (sibling question) | `Be honest — whether my sister is secretly mad at me?` | 240/243 |
| declarative_preference (:729) | acknowledge, cite the stored value | set_<theme/accent/font>{rejected value} with **no discover step** | `see to it that my Ditto accent is <value>` | 289/272 |

## 3. Catalog (`catalog/v13.go`, `catalog/v15.go`)

- **Size**: 233/234/235 (63/69/68 runs) = 30 product tools + 3–5 decoys + 200 connectors.
- **Product tools** (fixed relative order): create_image, edit_image, read_links, search_web, search_memories, search_subjects, fetch_memories, search_memories_in_subjects, artifacts, execute_agent_job, run_code, search_tools, list_agent_jobs, file_feedback_for_team, set_theme, set_reasoning_effort, set_chat_tool_preferences, discover_capabilities, save/update/delete_memory, calendar_create_event, calendar_search_events, gmail_send, set_accent_color, set_chat_font, create_workflow, list_workflows, list_schedules, run_workflow.
  - **Seeded**: every product description is one of 6 paraphrases per seed (`v13.go:180`; all 6 observed for every tool).
  - **Stable**: schemas. set_theme has enum system/light/dark/midnight/solarized and set_reasoning_effort has low/medium/high. The accent/font schemas say their options come only from discover_capabilities. set_main_model is retired.
- **Decoys**: 23 shapes, 3–5 per seed without replacement. The name is `<stem>_<suffix>` and the description is "Does… This is not…", which names the sibling product tool (e.g. "This is not run_code", "not gmail_send", "not read_links"). Each decoy is spliced at a seeded slot among the product tools. A non-bearer call returns "is not configured… Connect <Brand> in Settings".
- **Brand coining** (`CoinedStem`, `v13.go:641`): 2 or 3 CV syllables (p=½), C∈{b d f g k l m n p r s t v z}, V∈{a e i o u}, then p=½ a final from {l n r s t}; ~2.1M stems, no word filter. *Est.* with the starter kit's BERT vocab (18k whole words, names included) as English proxy: the stem law gives 2.1% exact words and 31% one edit from a ≥4-letter word. Observed over 801 brands: 13 (1.6%) words (side, motel, fuse, mule, ruse, votes, rites, gage, mare, mike, vera, toni, kala) and 257 (32%) one edit away (busil~basil, luler~ruler, figur~figure, mesan~mean; rigut~right was seen in an earlier corpus listing).
- **Connectors** (`v15.go`): a frozen pool of 277 tools across 136 apps. 200 are picked per seed by seeded permutation, kept in pool order, and spliced at seeded slots (each connector present in ~72% of runs). Each has one string param, one of 2 description variants, and the suffix "Needs the <App> connector to be linked in Settings." They are never correct, and every call is refused.
  - **69/277 names carry product verbs/nouns** (evernote_search_notes, circleci_rerun_workflow, databricks_run_job, hootsuite_schedule_post, ring_list_events, discord_send_message, reddit_list_saved…).
  - **Ordinary-word slugs**: monday, teams, box, linear, notion, ring, nest, square, ramp, pocket, buffer, segment, loom, zoom, steam, lever, sentry, sheets, excel, slack, obsidian, among others.

## 4. Hazards (counts over 200 runs unless stated)

| id | hazard | example | frequency |
|---|---|---|---|
| H1 | **Same surface, different correct move.** Restraint ask/act members share one grammar; state routes share one ask. | "For planning context …: Pop that into my calendar." → no tool vs calendar_create_event | 16 restraint + 13.7 state cases/run. 255 identical normalized prompts (quoted alias/numbers masked) map to ≥2 tool sets, covering 4,027 cases |
| H2 | **Category label ≠ prompt.** Six memory categories with six different expected lists carry the same planted questions; the expected list is not graded and any non-memory call scores 0. | "What's the code on my bike lock?" appears under all six | 4.5 + 2 reads/run (906 + 400 cases) |
| H3 | **Cue-inverted mutations.** Update prompts say scratch/bin/forget/remember; delete prompts say update/remember/save/clean up. | "Update my notes on Happy: … drop just that one" → delete_memory | update 647/647, delete 657/657 (100%) |
| H4 | **Memory verbs that route elsewhere.** | "Remember to tell me what's happening with X today" → search_web | "remember": delete 158, update 137, save 57, search_web 20 (of 372). "forget": update 124, search_web 36, **delete 0**. "remind": memory reads 355, list_schedules 39. "told you" → search_web 56/56 |
| H5 | **Named-then-negated cues.** | "Without going online, just tell me…" (ask), "open the actual page rather than relying on the search blurb", "not a one-off" | negation word in 2,243 prompts: no-tool only 286; the rest still expect a tool (world_theme 445, world_link 325, update 262, business 233…) |
| H6 | **Tool nouns in requests for another tool.** | "the image tool keeps timing out" → feedback; "enable image tools" → prefs; "turn on dark mode?" → discover_capabilities; "Code Mode" → run_code; "translator" (relation), "locker code" | feedback 200/200, prefs 200/200, capability 97/200, Code Mode 75/198. Keyword→tool: "chat"→set_chat_font 740; "email/mail"→delete_memory 487 vs gmail_send 215; "save/store/keep"→delete_memory 344 vs save_memory 40 |
| H7 | **Look-alike tools.** 1,113/2,000 decoy cases (56%) have a same-capability connector in the catalog (chat_post↔slack/teams/discord 109/109; tracker_issue↔linear/github/jira 79/79; sheet_rows↔excel 88/88; helpdesk↔zendesk 88/88; notebook↔notion 88/88; wiki/docs↔confluence 187/194); only the brand discriminates. Tool-discovery caps echo decoys/connectors (spreadsheet rows 77/77; file convert 17/65). Decoy "Not" sentences name product tools. | "Post to Lolos chat about the Daallo index…" beside slack_post_message | 10 decoy cases/run |
| H8 | **Connector/brand words in prompts.** | "monday" slug vs weekday; brand "Side" vs alias "sputnik side review"; online/google/drive/square/fedex/obsidian in org names | 713 prompt hits of a present connector's name word (online 343 from "Excel Online", monday 248, google 56); brand in other prompts 7 |
| H9 | **Figures under other labels** (`toolexec/v13.go:194`, `toolexec.go:465`): discover_capabilities always adds "Workspace limits: up to N saved workflows"; list_workflows "N total runs" vs list_schedules "N runs logged"; every needle sentence carries a decoy clause (other subject, seeded order/connective); chain snippets carry the scored decoy figure. | snippet number on link_chain → ×0 | cases/run through: discover 9.2, list_workflows 6.0, search→read 5.8, list_schedules 2.0, list_agent_jobs 2.0 |
| H10 | **Planning-context scope.** The prefix is the only join key between request and record; same-family records from other groups coexist in the store. (The label typos seen in dataset files are not served.) | "For planning context c0cd6fd0ee24d7aee: Stick it onto my schedule for me." | 1,574 cases (7.9/run), all with a clean prefix; two same-family groups in 53–57 runs per family |
| H11 | **Misspellings are deliberate and value-scoped** in served text. Appearance values are misspelled with up to floor(len/3) edits, plus a near-miss qualifier. The dataset files add a 70% typo pass (57.7% of prompts, 5.6% of tokens, measured over 30 seeds × 4 salts) that is **not served**, so a fix trained on file typos targets noise a live harness never sees. | "Switch Ditto's accent color to something like dakr tray" | ≈8.2% of served tool prompts (discovery 6.0 + world_theme 2.2 per run) |
| H12 | **Cadence names, not workflow names.** recipe_apply and schedules use the same 8-cadence pool; the coined name only appears in list_workflows. | "Run the saved workflow that goes hourly on weekdays." → run_workflow{name:"Dabedis digest"} | 200/200 each |
| H13 | **Appearance near-misses.** The edit-distance winner is the base option while the qualifier names the partner. Four accent surfaces have different tool sets: discovery and world_theme need discover+set; declarative act needs set only; declarative ask needs none. | "Switch my accent to the green shade of pie" → the qualified partner option, not the base | near-miss 400/1,200 (33%). Declarative accent+font+mode ≈ 2.8/run |
| H14 | **Closed intents.** Plain settings only resolve to system/dark and set_effort only to high/medium; low/light/midnight/solarized appear only in restraint/declarative cases. | "Sync Ditto's light or dark mode to my device" → system | settings 200, effort 137 |
| H15 | **Dependent arguments.** read_links needs the served URL; run_workflow needs the listed name; gmail_send body needs the needle; world email needs the *current* address. | — | ≈12 cases/run |
| H16 | **Vestigial JSON ground truth.** memory_fetch `required_args.pairIds` points at the accountant record, not the asked fact (172/172). The update `content` "handoff is X" is claim-graded (paraphrase OK). Settings verbatim grammars are dead. | — | — |
| H17 | **One shared store.** About 369 prerequisite pairs per run, of which ~341 sit on one carrier case whose category varies (contact 45, link 30, delete 26, update 25, theme 25, business 22, v10 18, email 6, calendar 3 of 200). | — | every run |
| H18 | **Order/ID/text shift.** Served order is HMAC-permuted; IDs become UUIDs; dataset-file prompt bytes differ from served bytes in 69% of cases. Never key on dataset position, case ID or file text. | — | every run |

Fix-scope guidance: H1, H2, H3, H10 and H13 are record-decided, so no surface rule can be right on both members. H4–H8 defeat keyword routers. H9 and H15 punish snippet-grepping.
