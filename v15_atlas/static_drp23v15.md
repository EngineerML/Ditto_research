# Static bench: static_drp23v15.jsonl

200 seeds at salt 0 (70000 requests); 200 datasets with salts 1-3 in all.

## Connector step

- tools left out per request: {200: 70000}
- connectors kept as linked by the request: {0: 70000}

## Tool families

| family | n | first-stage lane | records-lane share | product note (wrong / right) | live | top request kinds |
|---|---|---|---|---|---|---|
| agent_job | 109 | action:imperative 68, action:read-capability 16 | 0.0% | 0 / 0 | 0 | agent-job 55, - 51, artifact 3 |
| agent_jobs_result_usage | 197 | action:imperative 134, action:read-capability 63 | 0.0% | 0 / 0 | 0 | - 122, job-status 75 |
| agent_read_not_run | 200 | action:read-capability 169, action:imperative-setter 21 | 0.0% | 0 / 0 | 0 | job-status 187, - 13 |
| agent_run_not_read | 119 | action:imperative 70, action:default 20 | 0.0% | 0 / 0 | 0 | agent-job 116, - 3 |
| agent_workflow | 108 | action:imperative 84, action:imperative-setter 16 | 0.0% | 0 / 0 | 0 | workflow-new 95, - 7, repeat 6 |
| artifacts_create | 200 | action:imperative 150, action:request 26 | 0.0% | 0 / 0 | 0 | artifact 197, - 3 |
| automation_list | 200 | action:default 77, action:read-capability 74 | 0.0% | 0 / 0 | 0 | schedules 200 |
| automation_not_job | 112 | action:imperative 98, action:tool-hint 10 | 0.0% | 0 / 0 | 0 | repeat 90, workflow-new 22 |
| calendar_create | 128 | action:imperative 79, action:read-capability 28 | 0.0% | 0 / 0 | 0 | calendar-add 128 |
| calendar_search | 137 | action:imperative 64, action:read-capability 58 | 0.0% | 0 / 0 | 0 | - 107, calendar-find 30 |
| capability_discovery | 200 | action:read-capability 112, action:capability-question 43 | 1.5% | 0 / 0 | 0 | capabilities 119, how-to 71, - 9 |
| code_compute | 123 | action:arithmetic 123 | 0.0% | 0 / 0 | 0 | arithmetic 123 |
| code_compute_not_agent_job | 126 | action:arithmetic 59, action:read-capability 39 | 0.0% | 1 / 0 | 0 | arithmetic 125, product 1 |
| decoy_chat_message_result_usage | 109 | action:imperative-setter 71, action:imperative 38 | 0.0% | 0 / 109 | 0 | product 109 |
| decoy_contact_lookup_result_usage | 44 | action:imperative 44 | 0.0% | 0 / 44 | 0 | product 44 |
| decoy_crm_lookup_result_usage | 84 | action:imperative 84 | 0.0% | 0 / 84 | 0 | product 84 |
| decoy_docs_search_result_usage | 87 | action:imperative 87 | 0.0% | 0 / 87 | 0 | product 87 |
| decoy_file_convert_result_usage | 77 | action:imperative 77 | 0.0% | 0 / 77 | 0 | product 77 |
| decoy_inbox_triage_result_usage | 78 | action:imperative-setter 52, action:imperative 26 | 0.0% | 0 / 77 | 0 | product 77, - 1 |
| decoy_issue_create_result_usage | 79 | action:imperative 79 | 0.0% | 0 / 79 | 0 | product 79 |
| decoy_map_route_result_usage | 103 | action:imperative-setter 77, action:imperative 26 | 0.0% | 0 / 103 | 0 | product 103 |
| decoy_note_create_result_usage | 88 | action:imperative 88 | 0.0% | 0 / 88 | 0 | product 88 |
| decoy_poll_create_result_usage | 92 | action:imperative 92 | 0.0% | 0 / 92 | 0 | product 92 |
| decoy_price_quote_result_usage | 81 | action:imperative-setter 57, action:imperative 24 | 0.0% | 0 / 81 | 0 | product 81 |
| decoy_reminders_list_result_usage | 108 | action:imperative 108 | 0.0% | 0 / 107 | 0 | product 107, - 1 |
| decoy_sidebar_color_result_usage | 85 | action:imperative 55, action:imperative-setter 30 | 0.0% | 0 / 85 | 0 | product 85 |
| decoy_spreadsheet_read_result_usage | 88 | action:imperative 88 | 0.0% | 0 / 88 | 0 | product 88 |
| decoy_stock_quote_result_usage | 141 | action:imperative 98, action:imperative-setter 43 | 0.0% | 0 / 141 | 0 | product 141 |
| decoy_thesaurus_lookup_result_usage | 69 | action:imperative 69 | 0.0% | 0 / 69 | 0 | product 69 |
| decoy_ticket_lookup_result_usage | 88 | action:imperative 88 | 0.0% | 0 / 88 | 0 | product 88 |
| decoy_timer_start_result_usage | 88 | action:imperative 88 | 0.0% | 0 / 88 | 0 | product 88 |
| decoy_translate_text_result_usage | 52 | action:imperative 34, action:imperative-setter 18 | 0.0% | 0 / 52 | 0 | product 52 |
| decoy_unit_convert_result_usage | 80 | action:imperative 80 | 0.0% | 0 / 80 | 0 | product 80 |
| decoy_video_summarize_result_usage | 79 | action:imperative 40, action:imperative-setter 39 | 0.0% | 0 / 79 | 0 | product 79 |
| decoy_weather_lookup_result_usage | 93 | action:imperative 64, action:names-tool 29 | 0.0% | 0 / 93 | 0 | product 93 |
| decoy_wiki_search_result_usage | 107 | action:imperative 107 | 0.0% | 0 / 107 | 0 | product 107 |
| discovery_accent_set | 544 | action:imperative 544 | 0.0% | 0 / 0 | 0 | appearance-pick 544 |
| discovery_font_set | 656 | action:imperative 656 | 0.0% | 0 / 0 | 0 | appearance-pick 656 |
| entity_lookup_chain | 160 | records:question 95, action:default 53 | 0.0% | 0 / 0 | 0 | - 160 |
| feedback | 200 | action:imperative 137, action:imperative-setter 46 | 0.0% | 0 / 0 | 0 | feedback 200 |
| image_create | 124 | action:imperative 124 | 0.0% | 0 / 0 | 0 | - 124 |
| image_edit_not_create | 142 | action:imperative 44, action:request 37 | 2.1% | 0 / 0 | 0 | earlier-image 142 |
| link_chain_result_usage | 200 | action:imperative 122, action:look-up 75 | 0.0% | 1 / 0 | 0 | search-read 198, product 1, - 1 |
| memory_fetch | 172 | records:question 92, action:default 60 | 0.0% | 1 / 0 | 0 | - 171, product 1 |
| memory_lookup | 133 | records:question 84, action:default 42 | 0.0% | 0 / 0 | 0 | - 133 |
| memory_save_not_search | 200 | action:imperative 133, action:default 37 | 0.0% | 1 / 0 | 0 | save 162, - 37, product 1 |
| memory_subject | 141 | records:question 86, action:default 46 | 0.0% | 0 / 0 | 0 | - 141 |
| multi_image_edit | 126 | action:imperative 126 | 0.0% | 0 / 0 | 0 | - 126 |
| multi_subject_scope | 150 | records:question 88, action:default 46 | 0.0% | 0 / 0 | 0 | - 150 |
| multi_web_read | 114 | action:imperative 30, action:look-up 29 | 0.0% | 0 / 0 | 0 | search-read 114 |
| multi_web_result_usage | 200 | action:imperative 97, action:default 85 | 0.0% | 1 / 0 | 0 | search-read 199, product 1 |
| parallel_web_image | 133 | action:look-up 41, action:imperative 40 | 0.0% | 0 / 0 | 0 | - 70, web 63 |
| recipe_apply | 200 | action:imperative 200 | 0.0% | 0 / 0 | 0 | run-saved 200 |
| recipe_create | 113 | action:imperative 91, action:read-capability 22 | 0.0% | 0 / 0 | 0 | workflow-new 96, repeat 10, - 6 |
| route_memory_not_web | 150 | records:question 102, action:default 37 | 0.0% | 0 / 0 | 0 | - 150 |
| route_web_not_memory | 116 | action:live 92, action:imperative 20 | 0.9% | 0 / 0 | 0 | web 85, - 31 |
| sandbox_result_usage | 198 | action:imperative 128, action:imperative-setter 70 | 0.0% | 0 / 0 | 0 | sandbox 198 |
| schedules_result_usage | 200 | action:imperative 200 | 0.0% | 0 / 0 | 0 | schedules 200 |
| set_effort | 137 | action:default 72, action:imperative-setter 43 | 0.0% | 0 / 0 | 0 | effort-set 137 |
| set_tool_prefs | 200 | action:imperative-setter 95, action:imperative 89 | 0.0% | 0 / 0 | 0 | tool-prefs 200 |
| settings | 200 | action:read-capability 88, action:imperative 74 | 0.0% | 0 / 0 | 0 | colour-mode 200 |
| stale_context_web | 200 | action:live 110, action:imperative 89 | 0.0% | 1 / 0 | 0 | web 198, product 1, delete-one 1 |
| tool_discovery | 200 | action:imperative 112, action:imperative-setter 48 | 0.0% | 0 / 0 | 0 | tool-lookup 200 |
| tool_registry_result_usage | 199 | action:imperative 133, action:imperative-setter 66 | 0.0% | 1 / 0 | 0 | - 130, tool-lookup 68, product 1 |
| v10_state_dependent_routing | 1558 | action:imperative 1374, action:default 183 | 0.0% | 1 / 0 | 0 | agreed 1557, product 1 |
| v13_mutation_follow_up_read | 400 | records:question 257, records:stored-detail 141 | 0.0% | 0 / 0 | 0 | - 328, web 72 |
| v13_restraint_abstention_web | 483 | records:question 174, action:live 139 | 0.0% | 1 / 0 | 0 | - 375, web 107, product 1 |
| v13_restraint_calendar | 523 | action:read-capability 466, action:imperative-setter 37 | 0.0% | 0 / 0 | 0 | calendar-pending 523 |
| v13_restraint_declarative_preference | 561 | action:imperative 325, action:imperative-setter 150 | 0.0% | 0 / 0 | 0 | confirm-setting 561 |
| v13_restraint_effort | 520 | action:request 368, action:default 95 | 0.0% | 0 / 0 | 0 | effort 520 |
| v13_restraint_email | 531 | action:request 272, action:default 216 | 0.0% | 3 / 0 | 0 | planning-send 528, product 3 |
| v13_restraint_negation_web | 582 | action:imperative 157, action:read-capability 147 | 0.0% | 1 / 0 | 0 | no-web 285, web 211, - 85 |
| v13_state_dependent_calendar | 583 | action:imperative 204, action:imperative-setter 193 | 0.0% | 2 / 0 | 0 | calendar-named 581, product 2 |
| v13_state_dependent_email | 606 | action:default 396, action:imperative 210 | 0.0% | 0 / 0 | 0 | send 606 |
| web_recovery_result_usage | 200 | action:look-up 80, action:imperative 62 | 0.0% | 0 / 0 | 0 | web 173, - 27 |
| web_result_usage | 200 | action:imperative 102, action:look-up 58 | 0.0% | 1 / 0 | 0 | web 173, - 26, product 1 |
| web_search | 114 | action:live 44, action:imperative 25 | 0.0% | 0 / 0 | 0 | web 113, - 1 |
| workflow_not_job | 112 | action:imperative 71, action:imperative-setter 33 | 0.0% | 0 / 0 | 0 | workflow-new 112 |
| world_business_workflow | 489 | action:read-capability 253, action:imperative 231 | 0.0% | 0 / 0 | 0 | workflow 489 |
| world_contact_research_email_result_usage | 670 | action:request 459, action:live 103 | 0.0% | 0 / 0 | 0 | research-send 670 |
| world_link_chain_result_usage | 652 | action:live 337, action:imperative 315 | 0.0% | 0 / 0 | 0 | search-read 652 |
| world_memory_delete | 657 | action:imperative 501, action:default 142 | 0.0% | 1 / 0 | 0 | delete-one 656, product 1 |
| world_memory_update | 647 | action:imperative 509, action:default 137 | 0.0% | 1 / 0 | 0 | handoff 646, product 1 |
| world_theme_discover_set | 445 | action:imperative 217, action:read-capability 124 | 0.0% | 0 / 0 | 0 | appearance-pick 445 |

## Memory families

| family | n | action-lane share (first stage) | product note (wrong) | qtype (top) | qtype empty | top reasons |
|---|---|---|---|---|---|---|
| absence-cross-user | 600 | 0.0% | 0 | - 600 | 100.0% | records:question 389, records:stored-detail 211 |
| absence-false-premise | 800 | 1.4% | 0 | place-days 800 | 0.0% | records:question 789, action:imperative-setter 11 |
| absence-insufficient-composition | 800 | 0.6% | 0 | balance 800 | 0.0% | records:question 584, records:stored-figure 211 |
| absence-near-miss | 1000 | 0.7% | 0 | - 1000 | 100.0% | records:question 786, records:stored-detail 207 |
| absence-pure-absence | 1000 | 0.1% | 1 | - 1000 | 100.0% | records:question 973, records:stored-detail 26 |
| absence-stale-removed | 800 | 0.8% | 2 | handle 800 | 0.0% | records:question 528, records:stored-detail 266 |
| absence-twin-cross-user | 600 | 1.3% | 0 | - 600 | 100.0% | records:stored-detail 482, records:question 110 |
| absence-twin-false-premise | 800 | 0.0% | 0 | place-days 764, - 36 | 4.5% | records:question 800 |
| absence-twin-insufficient-composition | 800 | 6.4% | 2 | balance 800 | 0.0% | records:question 584, records:stored-figure 165 |
| absence-twin-near-miss | 1000 | 0.3% | 0 | - 1000 | 100.0% | records:stored-detail 805, records:question 192 |
| absence-twin-pure-absence | 1000 | 1.2% | 2 | - 1000 | 100.0% | records:stored-detail 790, records:question 198 |
| absence-twin-stale-removed | 800 | 2.5% | 1 | handle 800 | 0.0% | records:stored-detail 419, records:question 361 |
| conversational-chitchat | 600 | 29.5% | 0 | - 600 | 100.0% | records:question 423, action:default 95 |
| conversational-declarative | 600 | 100.0% | 0 | - 600 | 100.0% | action:setting-statement 600 |
| declarative-behavior | 600 | 35.2% | 1 | own-setting 600 | 0.0% | records:question 389, action:read-capability 108 |
| enterprise-composed-program | 2400 | 66.7% | 0 | - 2400 | 100.0% | action:live 1600, records:question 800 |
| injection-classic | 200 | 0.0% | 0 | owner 200 | 0.0% | records:question 200 |
| injection-data-inside-envelope | 400 | 20.5% | 2 | - 400 | 100.0% | records:question 318, action:imperative-setter 82 |
| injection-envelope-free | 200 | 0.0% | 1 | - 200 | 100.0% | records:stored-detail 200 |
| parser-divergence-hypothetical | 600 | 100.0% | 0 | - 600 | 100.0% | action:read-capability 600 |
| parser-divergence-negation | 600 | 100.0% | 0 | - 600 | 100.0% | action:live 600 |
| parser-divergence-reported-speech | 600 | 0.0% | 0 | - 600 | 100.0% | records:question 600 |
| parser-divergence-retraction | 600 | 0.0% | 0 | - 600 | 100.0% | records:question 600 |
| point-in-time-contact | 800 | 0.0% | 2 | asof 800 | 0.0% | records:question 707, records:stored-detail 93 |
| point-in-time-invoice | 800 | 8.0% | 1 | asof 800 | 0.0% | records:question 736, action:imperative-setter 49 |
| point-in-time-trip-leg | 800 | 0.8% | 0 | asof 800 | 0.0% | records:question 794, action:imperative 6 |
| record-quantity-cf-base | 1200 | 4.1% | 1 | - 999, direction 200 | 83.2% | records:question 1151, action:imperative-setter 49 |
| record-quantity-cf-variant | 1200 | 4.4% | 0 | - 1000, direction 200 | 83.3% | records:question 1147, action:imperative-setter 52 |
| record-quantity-direction | 800 | 17.2% | 1 | direction 800 | 0.0% | records:question 662, action:imperative-setter 138 |
| v13-open-program | 3200 | 30.5% | 10 | - 3200 | 100.0% | records:question 2225, action:live 544 |
| v13-personal-program | 4800 | 23.9% | 7 | - 4800 | 100.0% | records:question 3651, action:live 808 |
| world-canary | 200 | 100.0% | 0 | - 200 | 100.0% | action:read-capability 151, action:imperative-setter 49 |
| world-contact-current | 7 | 0.0% | 0 | - 7 | 100.0% | records:stored-detail 6, records:question 1 |
| world-contact-previous | 7 | 0.0% | 0 | - 7 | 100.0% | records:question 6, records:stored-detail 1 |
| world-isolation-contact-current | 1800 | 1.7% | 1 | - 1800 | 100.0% | records:stored-detail 1410, records:question 354 |
| world-project-lead-current | 46 | 39.1% | 1 | - 36, owner-email 10 | 78.3% | records:stored-detail 28, action:request 11 |
| world-project-lead-previous | 35 | 0.0% | 0 | - 35 | 100.0% | records:question 28, records:stored-detail 7 |
| world-project-outstanding | 28 | 3.6% | 0 | balance 22, - 6 | 21.4% | records:question 23, records:stored-figure 4 |
| world-story-lesson-claims | 800 | 2.0% | 0 | lesson 800 | 0.0% | records:question 784, action:read-capability 9 |
| world-story-next-action | 2600 | 23.7% | 2 | next 2600 | 0.0% | records:question 1710, action:default 350 |
| world-story-order | 2600 | 44.0% | 2 | order 2600 | 0.0% | records:question 1322, action:default 715 |
| world-story-owner-current | 2600 | 27.9% | 2 | owner 2600 | 0.0% | records:question 1874, action:live 671 |
| world-story-quantity | 1800 | 3.6% | 3 | quantity 1800 | 0.0% | records:question 1735, action:imperative-setter 23 |
| world-story-status-current | 2200 | 41.1% | 2 | status 2200 | 0.0% | records:question 1289, action:live 831 |
| world-story-status-disagree | 400 | 38.0% | 2 | disagree 400 | 0.0% | records:question 239, action:default 89 |
| world-story-x-owner-email | 2600 | 1.9% | 4 | owner-email 2600 | 0.0% | records:stored-detail 1968, records:question 543 |
| world-trip-changed-leg-current | 12 | 25.0% | 0 | place-days 9, trip-length 2 | 8.3% | records:question 9, action:live 2 |
| world-trip-changed-leg-previous | 23 | 0.0% | 0 | - 23 | 100.0% | records:question 23 |
| world-trip-current | 1218 | 0.1% | 0 | trip-length 1218 | 0.0% | records:question 1013, records:asked 204 |
| world-trip-longest-current | 24 | 29.2% | 0 | - 20, place-days 4 | 83.3% | records:question 17, action:live 7 |

## Salt sensitivity

0 seeds at salts 0-3. Total-variation distance of the (lane, request kind, qtype) mix against salt 0; families above 10%:

| family | salt 1 | salt 2 | salt 3 |
|---|---|---|---|
