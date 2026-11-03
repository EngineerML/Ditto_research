# Mock bench: 40 seeds, 14000 traced requests (0 unmatched)

Final lane after every store-dependent re-route (identifier, topic, answer-form). Unexpected = a tool case in the
records lane whose expected tools are not memory reads, or a memory question in the action lane.

| kind | family | n/run | unexpected | top lanes | top paths | hint |
|---|---|---|---|---|---|---|
| memory | conversational-declarative | 3.0 | 100% | action:setting-statement 120 | action 120 | 120 |
| memory | parser-divergence-hypothetical | 3.0 | 100% | action:read-capability 120 | action 120 | 0 |
| memory | world-canary | 1.0 | 100% | action:read-capability 32, action:imperative-setter 8 | action 40 | 0 |
| memory | conversational-chitchat | 3.0 | 28% | records:question 87, action:read-capability 19 | records 87, action 33 | 0 |
| memory | injection-data-inside-envelope | 2.0 | 19% | records:question 65, action:imperative-setter 15 | records 65, action 15 | 0 |
| memory | world-project-lead-current | 0.2 | 11% | records:stored-detail 6, records:answer-form 2 | records 8, action 1 | 0 |
| tool | capability_discovery | 1.0 | 5% | action:read-capability 19, action:capability-question 12 | action 38, records 2 | 38 |
| memory | record-quantity-cf-variant | 6.0 | 2% | records:question 234, action:imperative-setter 5 | records 235, action 5 | 5 |
| memory | record-quantity-cf-base | 6.0 | 2% | records:question 233, action:imperative-setter 4 | records 236, action 4 | 2 |
| memory | absence-twin-insufficient-composition | 4.0 | 1% | records:question 118, records:stored-figure 35 | records 158, action 2 | 0 |
| memory | world-isolation-contact-current | 9.0 | 1% | records:stored-detail 279, records:question 78 | records 357, action 3 | 2 |
| memory | absence-twin-stale-removed | 4.0 | 1% | records:stored-detail 82, records:question 74 | records 159, action 1 | 0 |
| memory | absence-near-miss | 5.0 | 0% | records:question 158, records:stored-detail 41 | records 199, action 1 | 0 |
| memory | absence-twin-pure-absence | 5.0 | 0% | records:stored-detail 150, records:question 49 | records 199, action 1 | 0 |
| memory | absence-cross-user | 3.0 | 0% | records:question 77, records:stored-detail 43 | records 113, topic 7 | 0 |
| memory | absence-false-premise | 4.0 | 0% | records:question 158, records:answer-form 2 | records 160 | 0 |
| memory | absence-insufficient-composition | 4.0 | 0% | records:question 116, records:stored-figure 44 | records 160 | 0 |
| memory | absence-pure-absence | 5.0 | 0% | records:question 194, records:stored-detail 6 | records 199, topic 1 | 0 |
| memory | absence-stale-removed | 4.0 | 0% | records:question 111, records:stored-detail 49 | records 160 | 0 |
| memory | absence-twin-cross-user | 3.0 | 0% | records:stored-detail 96, records:question 24 | records 120 | 0 |
| memory | absence-twin-false-premise | 4.0 | 0% | records:question 160 | records 160 | 0 |
| memory | absence-twin-near-miss | 5.0 | 0% | records:stored-detail 153, records:question 47 | records 200 | 0 |
| memory | declarative-behavior | 3.0 | 0% | records:question 82, records:answer-form 25 | records 120 | 0 |
| memory | enterprise-composed-program | 12.0 | 0% | records:identifier 320, records:question 160 | records 480 | 0 |
| memory | injection-classic | 1.0 | 0% | records:question 40 | records 40 | 0 |
| memory | injection-envelope-free | 1.0 | 0% | records:stored-detail 40 | records 40 | 0 |
| memory | parser-divergence-negation | 3.0 | 0% | records:own-records 120 | records 120 | 0 |
| memory | parser-divergence-reported-speech | 3.0 | 0% | records:question 120 | records 120 | 0 |
| memory | parser-divergence-retraction | 3.0 | 0% | records:question 120 | records 120 | 0 |
| memory | point-in-time-contact | 4.0 | 0% | records:question 136, records:stored-detail 24 | records 160 | 0 |
| memory | point-in-time-invoice | 4.0 | 0% | records:question 144, records:answer-form 16 | records 160 | 0 |
| memory | point-in-time-trip-leg | 4.0 | 0% | records:question 159, records:answer-form 1 | records 160 | 0 |
| memory | record-quantity-direction | 4.0 | 0% | records:question 140, records:answer-form 20 | records 160 | 0 |
| memory | v13-open-program | 16.0 | 0% | records:question 456, records:identifier 104 | program 640 | 0 |
| memory | v13-personal-program | 24.0 | 0% | records:question 750, records:identifier 146 | program 952, records 8 | 0 |
| memory | world-contact-current | 0.0 | 0% | records:stored-detail 1 | records 1 | 0 |
| memory | world-project-lead-previous | 0.3 | 0% | records:question 12, records:stored-detail 1 | records 13 | 0 |
| memory | world-project-outstanding | 0.1 | 0% | records:question 2, records:stored-figure 1 | records 3 | 0 |
| memory | world-story-lesson-claims | 4.0 | 0% | records:question 156, records:topic 4 | topic 160 | 0 |
| memory | world-story-next-action | 13.0 | 0% | records:question 354, records:topic 84 | topic 520 | 0 |
| memory | world-story-order | 13.0 | 0% | records:question 259, records:answer-form 134 | topic 520 | 0 |
| memory | world-story-owner-current | 13.0 | 0% | records:question 362, records:own-records 139 | topic 520 | 0 |
| memory | world-story-quantity | 9.0 | 0% | records:question 344, records:topic 16 | topic 360 | 0 |
| memory | world-story-status-current | 11.0 | 0% | records:question 250, records:own-records 141 | topic 440 | 0 |
| memory | world-story-status-disagree | 2.0 | 0% | records:question 41, records:topic 15 | topic 80 | 0 |
| memory | world-story-x-owner-email | 13.0 | 0% | records:stored-detail 405, records:question 103 | topic 519, records 1 | 0 |
| memory | world-trip-changed-leg-current | 0.1 | 0% | records:question 2 | records 2 | 0 |
| memory | world-trip-changed-leg-previous | 0.1 | 0% | records:question 5 | records 5 | 0 |
| memory | world-trip-current | 6.0 | 0% | records:question 198, records:asked 44 | records 242 | 0 |
| memory | world-trip-longest-current | 0.1 | 0% | records:question 4, records:own-records 1 | records 5 | 0 |
| tool | agent_job | 0.5 | 0% | action:imperative 12, action:read-capability 3 | action 21 | 13 |
| tool | agent_jobs_result_usage | 1.0 | 0% | action:imperative 28, action:read-capability 12 | action 40 | 21 |
| tool | agent_read_not_run | 1.0 | 0% | action:read-capability 32, action:imperative-setter 7 | action 40 | 38 |
| tool | agent_run_not_read | 0.6 | 0% | action:imperative 12, action:default 7 | action 24 | 24 |
| tool | agent_workflow | 0.6 | 0% | action:imperative 18, action:imperative-setter 6 | action 25 | 22 |
| tool | artifacts_create | 1.0 | 0% | action:imperative 29, action:request 5 | action 40 | 39 |
| tool | automation_list | 1.0 | 0% | action:read-capability 17, action:live 9 | action 40 | 40 |
| tool | automation_not_job | 0.5 | 0% | action:imperative 18, action:tool-hint 3 | action 21 | 21 |
| tool | calendar_create | 0.7 | 0% | action:imperative 20, action:read-capability 5 | action 27 | 27 |
| tool | calendar_search | 0.7 | 0% | action:read-capability 12, action:imperative 9 | action 29 | 8 |
| tool | code_compute | 0.6 | 0% | action:arithmetic 25 | action 25 | 25 |
| tool | code_compute_not_agent_job | 0.6 | 0% | action:arithmetic 14, action:live 6 | action 23 | 23 |
| tool | decoy_chat_message_result_usage | 0.6 | 0% | action:imperative-setter 16, action:imperative 7 | action 23 | 23 |
| tool | decoy_contact_lookup_result_usage | 0.2 | 0% | action:imperative 7 | action 7 | 7 |
| tool | decoy_crm_lookup_result_usage | 0.3 | 0% | action:imperative 12 | action 12 | 12 |
| tool | decoy_docs_search_result_usage | 0.7 | 0% | action:imperative 27 | action 27 | 27 |
| tool | decoy_file_convert_result_usage | 0.4 | 0% | action:imperative 17 | action 17 | 17 |
| tool | decoy_inbox_triage_result_usage | 0.2 | 0% | action:imperative-setter 8, action:imperative 1 | action 9 | 9 |
| tool | decoy_issue_create_result_usage | 0.4 | 0% | action:imperative 15 | action 15 | 15 |
| tool | decoy_map_route_result_usage | 0.5 | 0% | action:imperative-setter 14, action:imperative 5 | action 19 | 19 |
| tool | decoy_note_create_result_usage | 0.6 | 0% | action:imperative 22 | action 22 | 22 |
| tool | decoy_poll_create_result_usage | 0.5 | 0% | action:imperative 19 | action 19 | 19 |
| tool | decoy_price_quote_result_usage | 0.4 | 0% | action:imperative-setter 11, action:imperative 5 | action 16 | 16 |
| tool | decoy_reminders_list_result_usage | 0.6 | 0% | action:imperative 25 | action 25 | 25 |
| tool | decoy_sidebar_color_result_usage | 0.6 | 0% | action:imperative 14, action:imperative-setter 8 | action 22 | 22 |
| tool | decoy_spreadsheet_read_result_usage | 0.3 | 0% | action:imperative 11 | action 11 | 11 |
| tool | decoy_stock_quote_result_usage | 0.8 | 0% | action:imperative 23, action:imperative-setter 9 | action 32 | 32 |
| tool | decoy_thesaurus_lookup_result_usage | 0.1 | 0% | action:imperative 4 | action 4 | 4 |
| tool | decoy_ticket_lookup_result_usage | 0.4 | 0% | action:imperative 16 | action 16 | 16 |
| tool | decoy_timer_start_result_usage | 0.8 | 0% | action:imperative 32 | action 32 | 32 |
| tool | decoy_translate_text_result_usage | 0.1 | 0% | action:imperative 4, action:imperative-setter 1 | action 5 | 5 |
| tool | decoy_unit_convert_result_usage | 0.6 | 0% | action:imperative 22 | action 22 | 22 |
| tool | decoy_video_summarize_result_usage | 0.2 | 0% | action:imperative-setter 5, action:imperative 4 | action 9 | 9 |
| tool | decoy_weather_lookup_result_usage | 0.5 | 0% | action:imperative 10, action:names-tool 8 | action 18 | 18 |
| tool | decoy_wiki_search_result_usage | 0.5 | 0% | action:imperative 18 | action 18 | 18 |
| tool | discovery_accent_set | 2.8 | 0% | action:imperative 112 | action 112 | 112 |
| tool | discovery_font_set | 3.2 | 0% | action:imperative 128 | action 128 | 128 |
| tool | entity_lookup_chain | 0.9 | 0% | records:question 21, action:default 11 | records 24, action 11 | 0 |
| tool | feedback | 1.0 | 0% | action:imperative 28, action:imperative-setter 9 | action 40 | 40 |
| tool | image_create | 0.6 | 0% | action:imperative 25 | action 25 | 0 |
| tool | image_edit_not_create | 0.7 | 0% | action:request 7, action:default 6 | action 27 | 27 |
| tool | link_chain_result_usage | 1.0 | 0% | action:imperative 21, action:look-up 19 | action 40 | 40 |
| tool | memory_fetch | 0.8 | 0% | records:question 15, action:default 12 | action 17, records 15 | 0 |
| tool | memory_lookup | 0.6 | 0% | action:default 11, records:question 11 | records 12, action 11 | 0 |
| tool | memory_save_not_search | 1.0 | 0% | action:imperative 31, action:request 6 | action 40 | 37 |
| tool | memory_subject | 0.8 | 0% | records:question 22, action:default 6 | records 23, action 7 | 0 |
| tool | multi_image_edit | 0.6 | 0% | action:imperative 24 | action 24 | 0 |
| tool | multi_subject_scope | 0.6 | 0% | records:question 16, action:default 6 | records 17, action 7 | 0 |
| tool | multi_web_read | 0.6 | 0% | action:default 7, action:read-capability 7 | action 25 | 25 |
| tool | multi_web_result_usage | 1.0 | 0% | action:imperative 26, action:default 13 | action 40 | 40 |
| tool | parallel_web_image | 0.7 | 0% | action:imperative 9, action:read-capability 9 | action 29 | 13 |
| tool | recipe_apply | 1.0 | 0% | action:imperative 40 | action 40 | 40 |
| tool | recipe_create | 0.6 | 0% | action:imperative 20, action:read-capability 4 | action 24 | 24 |
| tool | route_memory_not_web | 0.7 | 0% | records:question 16, action:default 10 | records 16, action 10 | 0 |
| tool | route_web_not_memory | 0.7 | 0% | action:live 18, action:imperative 9 | action 27 | 19 |
| tool | sandbox_result_usage | 1.0 | 0% | action:imperative 28, action:imperative-setter 12 | action 40 | 40 |
| tool | schedules_result_usage | 1.0 | 0% | action:imperative 40 | action 40 | 40 |
| tool | set_effort | 0.7 | 0% | action:default 16, action:imperative-setter 8 | action 28 | 28 |
| tool | set_tool_prefs | 1.0 | 0% | action:imperative 21, action:imperative-setter 16 | action 40 | 40 |
| tool | settings | 1.0 | 0% | action:read-capability 20, action:imperative 15 | action 40 | 40 |
| tool | stale_context_web | 1.0 | 0% | action:live 21, action:imperative 19 | action 40 | 40 |
| tool | tool_discovery | 1.0 | 0% | action:imperative 17, action:imperative-setter 13 | action 40 | 40 |
| tool | tool_registry_result_usage | 1.0 | 0% | action:imperative 26, action:imperative-setter 14 | action 40 | 14 |
| tool | v10_state_dependent_routing | 8.4 | 0% | action:imperative 301, action:default 35 | action 336 | 336 |
| tool | v13_mutation_follow_up_read | 2.0 | 0% | records:question 53, records:stored-detail 27 | records 80 | 0 |
| tool | v13_restraint_abstention_web | 2.8 | 0% | records:question 45, action:live 32 | action 67, records 45 | 30 |
| tool | v13_restraint_calendar | 3.7 | 0% | action:read-capability 132, action:imperative-setter 9 | action 148 | 148 |
| tool | v13_restraint_declarative_preference | 2.9 | 0% | action:imperative 72, action:imperative-setter 23 | action 115 | 115 |
| tool | v13_restraint_effort | 2.2 | 0% | action:request 53, action:default 30 | action 90 | 90 |
| tool | v13_restraint_email | 2.4 | 0% | action:default 45, action:request 40 | action 96 | 96 |
| tool | v13_restraint_negation_web | 2.0 | 0% | action:read-capability 23, action:look-up 21 | action 72, records 7 | 64 |
| tool | v13_state_dependent_calendar | 2.7 | 0% | action:read-capability 37, action:imperative-setter 37 | action 109 | 109 |
| tool | v13_state_dependent_email | 2.9 | 0% | action:default 80, action:imperative 34 | action 114 | 114 |
| tool | web_recovery_result_usage | 1.0 | 0% | action:look-up 17, action:imperative 12 | action 40 | 37 |
| tool | web_result_usage | 1.0 | 0% | action:imperative 19, action:look-up 9 | action 40 | 30 |
| tool | web_search | 0.6 | 0% | action:live 9, action:imperative 6 | action 23 | 23 |
| tool | workflow_not_job | 0.7 | 0% | action:imperative 13, action:imperative-setter 12 | action 26 | 26 |
| tool | world_business_workflow | 2.3 | 0% | action:read-capability 48, action:imperative 44 | action 93 | 93 |
| tool | world_contact_research_email_result_usage | 3.5 | 0% | action:request 95, action:imperative 20 | action 131, action+topic 8 | 139 |
| tool | world_link_chain_result_usage | 3.2 | 0% | action:live 72, action:imperative 56 | action 126, action+topic 2 | 128 |
| tool | world_memory_delete | 3.1 | 0% | action:imperative 100, action:default 24 | action 124, action+topic 2 | 126 |
| tool | world_memory_update | 3.2 | 0% | action:imperative 108, action:default 19 | action 128 | 128 |
| tool | world_theme_discover_set | 2.0 | 0% | action:imperative 43, action:imperative-setter 23 | action 82 | 82 |
