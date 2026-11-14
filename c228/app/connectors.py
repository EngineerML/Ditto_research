"""The public connector pool of the bench-15/16 catalog (research/dittobench-datagen/catalog/v15.go, connectorPool).

Each entry is (app slug, app name, the app's tool names). Bench 16 connector descriptions no longer say whether an app
is linked, so the harness shows an app's tools only when the request names that app (policy v13 W4 clarification of
2026-11-03: filtering connector or app-specific tools on the request's app-name wording). A static list of the public
pool is permitted; tools outside it (every product tool) are never hidden by this filter.
"""
from __future__ import annotations

CONNECTOR_POOL: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("slack", "Slack", ("slack_post_message", "slack_list_channels", "slack_search_messages", "slack_set_status")),
    ("notion", "Notion", ("notion_create_page", "notion_search_pages", "notion_append_block", "notion_query_database")),
    ("linear", "Linear", ("linear_create_issue", "linear_list_issues", "linear_update_issue", "linear_list_cycles")),
    ("jira", "Jira", ("jira_create_ticket", "jira_search_tickets", "jira_transition_ticket", "jira_add_worklog")),
    ("github", "GitHub", ("github_list_pull_requests", "github_create_issue", "github_get_file", "github_list_workflow_runs", "github_merge_pull_request")),
    ("gitlab", "GitLab", ("gitlab_list_merge_requests", "gitlab_create_issue", "gitlab_list_pipelines")),
    ("asana", "Asana", ("asana_create_task", "asana_list_tasks", "asana_complete_task")),
    ("trello", "Trello", ("trello_create_card", "trello_move_card", "trello_list_boards")),
    ("clickup", "ClickUp", ("clickup_create_task", "clickup_list_spaces", "clickup_track_time")),
    ("monday", "monday.com", ("monday_create_item", "monday_list_boards", "monday_update_column")),
    ("airtable", "Airtable", ("airtable_list_records", "airtable_create_record", "airtable_list_bases")),
    ("confluence", "Confluence", ("confluence_create_page", "confluence_get_page", "confluence_list_spaces")),
    ("figma", "Figma", ("figma_list_files", "figma_get_comments", "figma_export_frame")),
    ("salesforce", "Salesforce", ("salesforce_query_records", "salesforce_create_lead", "salesforce_update_opportunity", "salesforce_log_call")),
    ("hubspot", "HubSpot", ("hubspot_create_deal", "hubspot_list_deals", "hubspot_enroll_sequence")),
    ("pipedrive", "Pipedrive", ("pipedrive_list_deals", "pipedrive_add_activity")),
    ("zendesk", "Zendesk", ("zendesk_search_tickets", "zendesk_reply_ticket", "zendesk_assign_ticket")),
    ("intercom", "Intercom", ("intercom_list_conversations", "intercom_reply_conversation", "intercom_tag_user")),
    ("freshdesk", "Freshdesk", ("freshdesk_create_ticket", "freshdesk_list_tickets")),
    ("stripe", "Stripe", ("stripe_list_charges", "stripe_create_invoice", "stripe_refund_charge", "stripe_list_subscriptions")),
    ("shopify", "Shopify", ("shopify_list_orders", "shopify_update_inventory", "shopify_create_discount")),
    ("quickbooks", "QuickBooks", ("quickbooks_list_invoices", "quickbooks_create_bill", "quickbooks_run_report")),
    ("xero", "Xero", ("xero_list_invoices", "xero_reconcile_transaction")),
    ("dropbox", "Dropbox", ("dropbox_list_folder", "dropbox_share_link", "dropbox_upload_file")),
    ("box", "Box", ("box_search_files", "box_list_collaborators")),
    ("onedrive", "OneDrive", ("onedrive_list_items", "onedrive_share_item")),
    ("googledrive", "Google Drive", ("googledrive_search_files", "googledrive_create_folder", "googledrive_move_file")),
    ("sheets", "Google Sheets", ("sheets_append_row", "sheets_create_spreadsheet")),
    ("excel", "Excel Online", ("excel_read_range", "excel_write_range")),
    ("teams", "Microsoft Teams", ("teams_post_message", "teams_list_teams")),
    ("discord", "Discord", ("discord_send_message", "discord_list_servers")),
    ("zoom", "Zoom", ("zoom_list_recordings",)),
    ("sentry", "Sentry", ("sentry_list_issues", "sentry_resolve_issue")),
    ("pagerduty", "PagerDuty", ("pagerduty_list_incidents", "pagerduty_acknowledge_incident", "pagerduty_who_is_on_call")),
    ("datadog", "Datadog", ("datadog_query_metrics", "datadog_list_monitors", "datadog_mute_monitor")),
    ("vercel", "Vercel", ("vercel_list_deployments", "vercel_promote_deployment")),
    ("netlify", "Netlify", ("netlify_list_sites", "netlify_trigger_build")),
    ("cloudflare", "Cloudflare", ("cloudflare_list_dns_records", "cloudflare_purge_cache")),
    ("aws", "AWS", ("aws_list_buckets", "aws_describe_instances")),
    ("twilio", "Twilio", ("twilio_send_sms", "twilio_list_calls")),
    ("docusign", "DocuSign", ("docusign_send_envelope", "docusign_envelope_status")),
    ("greenhouse", "Greenhouse", ("greenhouse_list_candidates", "greenhouse_schedule_interview")),
    ("workday", "Workday", ("workday_request_time_off", "workday_get_payslip")),
    ("gusto", "Gusto", ("gusto_run_payroll", "gusto_list_employees")),
    ("spotify", "Spotify", ("spotify_play_playlist", "spotify_add_to_queue")),
    ("strava", "Strava", ("strava_list_activities", "strava_upload_activity")),
    ("uber", "Uber", ("uber_request_ride", "uber_ride_history")),
    ("doordash", "DoorDash", ("doordash_search_restaurants", "doordash_track_order")),
    ("instacart", "Instacart", ("instacart_add_to_cart", "instacart_list_orders")),
    ("opentable", "OpenTable", ("opentable_find_table", "opentable_cancel_reservation")),
    ("airbnb", "Airbnb", ("airbnb_search_stays", "airbnb_list_trips")),
    ("reddit", "Reddit", ("reddit_submit_post", "reddit_list_saved")),
    ("linkedin", "LinkedIn", ("linkedin_share_post", "linkedin_list_connections")),
    ("mixpanel", "Mixpanel", ("mixpanel_query_funnel", "mixpanel_list_cohorts")),
    ("amplitude", "Amplitude", ("amplitude_event_segmentation", "amplitude_list_charts")),
    ("snowflake", "Snowflake", ("snowflake_run_query", "snowflake_list_warehouses")),
    ("bigquery", "BigQuery", ("bigquery_run_query", "bigquery_list_datasets")),
    ("postgres", "Postgres", ("postgres_run_query", "postgres_list_tables")),
    ("webflow", "Webflow", ("webflow_publish_site", "webflow_list_collection_items")),
    ("wordpress", "WordPress", ("wordpress_create_post", "wordpress_list_comments")),
    ("typeform", "Typeform", ("typeform_list_responses", "typeform_create_form")),
    ("1password", "1Password", ("1password_list_vaults", "1password_share_item")),
    ("okta", "Okta", ("okta_list_apps", "okta_reset_factor")),
    ("basecamp", "Basecamp", ("basecamp_post_update", "basecamp_list_todos", "basecamp_complete_todo")),
    ("smartsheet", "Smartsheet", ("smartsheet_list_sheets", "smartsheet_update_row")),
    ("miro", "Miro", ("miro_create_sticky", "miro_list_boards", "miro_export_board")),
    ("loom", "Loom", ("loom_list_videos", "loom_share_video")),
    ("gong", "Gong", ("gong_list_calls", "gong_call_stats")),
    ("outreach", "Outreach", ("outreach_add_prospect", "outreach_list_sequences")),
    ("marketo", "Marketo", ("marketo_list_programs", "marketo_add_to_list")),
    ("segment", "Segment", ("segment_list_sources", "segment_track_event")),
    ("looker", "Looker", ("looker_run_look", "looker_list_dashboards")),
    ("tableau", "Tableau", ("tableau_list_workbooks", "tableau_refresh_extract")),
    ("metabase", "Metabase", ("metabase_run_question", "metabase_list_collections")),
    ("databricks", "Databricks", ("databricks_run_job", "databricks_list_clusters")),
    ("mongodb", "MongoDB Atlas", ("mongodb_find_documents", "mongodb_list_clusters")),
    ("supabase", "Supabase", ("supabase_run_sql", "supabase_list_projects")),
    ("firebase", "Firebase", ("firebase_list_users", "firebase_deploy_rules")),
    ("heroku", "Heroku", ("heroku_list_apps", "heroku_restart_dynos", "heroku_tail_logs")),
    ("digitalocean", "DigitalOcean", ("digitalocean_list_droplets", "digitalocean_resize_droplet")),
    ("azure", "Azure", ("azure_list_resource_groups", "azure_start_vm")),
    ("gcp", "Google Cloud", ("gcp_list_instances", "gcp_read_logs")),
    ("kubernetes", "Kubernetes", ("kubernetes_list_pods", "kubernetes_scale_deployment")),
    ("terraform", "Terraform Cloud", ("terraform_list_runs", "terraform_queue_plan")),
    ("circleci", "CircleCI", ("circleci_list_pipelines", "circleci_rerun_workflow")),
    ("bitbucket", "Bitbucket", ("bitbucket_list_pull_requests", "bitbucket_create_branch")),
    ("grafana", "Grafana", ("grafana_list_dashboards", "grafana_silence_alert")),
    ("statuspage", "Statuspage", ("statuspage_create_incident", "statuspage_list_components")),
    ("opsgenie", "Opsgenie", ("opsgenie_list_alerts", "opsgenie_close_alert")),
    ("brex", "Brex", ("brex_list_expenses", "brex_upload_receipt")),
    ("ramp", "Ramp", ("ramp_list_transactions", "ramp_request_card")),
    ("expensify", "Expensify", ("expensify_create_report", "expensify_submit_report")),
    ("paypal", "PayPal", ("paypal_list_transactions", "paypal_send_invoice")),
    ("square", "Square", ("square_list_payments", "square_update_item")),
    ("plaid", "Plaid", ("plaid_list_accounts", "plaid_refresh_balances")),
    ("etsy", "Etsy", ("etsy_list_listings", "etsy_list_receipts")),
    ("amazon_seller", "Amazon Seller Central", ("amazon_seller_list_orders", "amazon_seller_inventory_summary")),
    ("ups", "UPS", ("ups_track_package", "ups_create_label")),
    ("fedex", "FedEx", ("fedex_track_package", "fedex_schedule_pickup")),
    ("canvas_lms", "Canvas LMS", ("canvas_lms_list_courses", "canvas_lms_list_assignments")),
    ("duolingo", "Duolingo", ("duolingo_streak_status",)),
    ("peloton", "Peloton", ("peloton_list_workouts",)),
    ("fitbit", "Fitbit", ("fitbit_sleep_log", "fitbit_step_count")),
    ("myfitnesspal", "MyFitnessPal", ("myfitnesspal_log_food",)),
    ("goodreads", "Goodreads", ("goodreads_add_to_shelf",)),
    ("letterboxd", "Letterboxd", ("letterboxd_log_film",)),
    ("steam", "Steam", ("steam_list_library",)),
    ("twitch", "Twitch", ("twitch_list_followed",)),
    ("sonos", "Sonos", ("sonos_set_volume", "sonos_group_rooms")),
    ("philips_hue", "Philips Hue", ("philips_hue_set_scene",)),
    ("nest", "Nest", ("nest_set_temperature",)),
    ("ring", "Ring", ("ring_list_events",)),
    ("tesla", "Tesla", ("tesla_vehicle_status", "tesla_precondition")),
    ("lyft", "Lyft", ("lyft_request_ride",)),
    ("expedia", "Expedia", ("expedia_search_flights", "expedia_list_itineraries")),
    ("tripit", "TripIt", ("tripit_list_trips",)),
    ("zapier", "Zapier", ("zapier_list_zaps", "zapier_toggle_zap")),
    ("ifttt", "IFTTT", ("ifttt_list_applets",)),
    ("mailgun", "Mailgun", ("mailgun_list_bounces",)),
    ("sendgrid", "SendGrid", ("sendgrid_list_suppressions",)),
    ("bamboohr", "BambooHR", ("bamboohr_whos_out", "bamboohr_employee_directory")),
    ("lever", "Lever", ("lever_list_opportunities",)),
    ("rippling", "Rippling", ("rippling_list_devices",)),
    ("vanta", "Vanta", ("vanta_list_failing_tests",)),
    ("snyk", "Snyk", ("snyk_list_vulnerabilities",)),
    ("postman", "Postman", ("postman_run_collection",)),
    ("readwise", "Readwise", ("readwise_list_highlights",)),
    ("pocket", "Pocket", ("pocket_list_saved",)),
    ("evernote", "Evernote", ("evernote_search_notes",)),
    ("obsidian", "Obsidian Sync", ("obsidian_list_vault_files",)),
    ("coda", "Coda", ("coda_list_docs", "coda_upsert_row")),
    ("quip", "Quip", ("quip_list_threads",)),
    ("hootsuite", "Hootsuite", ("hootsuite_schedule_post",)),
    ("buffer", "Buffer", ("buffer_list_queue",)),
    ("canny", "Canny", ("canny_list_posts",)),
    ("productboard", "Productboard", ("productboard_list_features",)),
)

import re

# App names that are also ordinary words match only as written with a capital letter ("Teams", "Box", "Sheets").
CASED_NAMES = frozenset({"Box", "Teams", "Sheets", "Excel", "Zoom", "Uber", "Monday"})
TOOL_APP: dict[str, int] = {tool: index for index, (_, _, tools) in enumerate(CONNECTOR_POOL) for tool in tools}

# Each scripted app reads with one tool and writes with one (the catalog's connector scripts): a lookup in the app is its reading
# tool, posting or recording something in it is its writing tool, and the app's other tools are neither.
CONNECTOR_SCRIPT: dict[str, tuple[str, str]] = {
    "slack": ("search_messages", "post_message"), "notion": ("query_database", "create_page"), "linear": ("list_issues", "create_issue"),
    "jira": ("search_tickets", "create_ticket"), "github": ("list_pull_requests", "create_issue"), "asana": ("list_tasks", "create_task"),
    "trello": ("list_boards", "create_card"), "clickup": ("list_spaces", "create_task"), "hubspot": ("list_deals", "create_deal"),
    "salesforce": ("query_records", "create_lead"), "confluence": ("get_page", "create_page"), "freshdesk": ("list_tickets", "create_ticket"),
    "gitlab": ("list_merge_requests", "create_issue"), "monday": ("list_boards", "create_item"), "basecamp": ("list_todos", "post_update"),
    "teams": ("list_teams", "post_message"), "discord": ("list_servers", "send_message"), "miro": ("list_boards", "create_sticky"),
    "wordpress": ("list_comments", "create_post"), "typeform": ("list_responses", "create_form"), "statuspage": ("list_components", "create_incident"),
    "googledrive": ("search_files", "create_folder"), "pipedrive": ("list_deals", "add_activity"), "quickbooks": ("list_invoices", "create_bill"),
}
APP_READ_TOOL: dict[int, str] = {index: f"{slug}_{CONNECTOR_SCRIPT[slug][0]}" for index, (slug, _, tools) in enumerate(CONNECTOR_POOL) if slug in CONNECTOR_SCRIPT and f"{slug}_{CONNECTOR_SCRIPT[slug][0]}" in tools}
APP_WRITE_TOOL: dict[int, str] = {index: f"{slug}_{CONNECTOR_SCRIPT[slug][1]}" for index, (slug, _, tools) in enumerate(CONNECTOR_POOL) if slug in CONNECTOR_SCRIPT and f"{slug}_{CONNECTOR_SCRIPT[slug][1]}" in tools}


def _forms(slug: str, name: str) -> list[str]:
    forms = {name}
    for prefix in ("Google ", "Microsoft "):
        if name.startswith(prefix):
            forms.add(name[len(prefix):])
    if name.endswith(" Online"):
        forms.add(name[: -len(" Online")])
    if name.endswith(".com"):
        forms.add(name[: -len(".com")].capitalize() + ".com")
    if " " not in name and "." not in name and slug.replace("_", "") == name.lower():
        forms.add(slug)
    return sorted(forms)


def _pattern(slug: str, name: str) -> re.Pattern[str]:
    cased = [re.escape(form) for form in _forms(slug, name) if form in CASED_NAMES or form.capitalize() in CASED_NAMES and form[:1].isupper()]
    loose = [re.escape(form) for form in _forms(slug, name) if form not in CASED_NAMES and form.capitalize() not in CASED_NAMES]
    parts = []
    if loose:
        parts.append(r"(?i:(?<![A-Za-z0-9])(?:" + "|".join(loose) + r")(?![A-Za-z0-9]))")
    if cased:
        parts.append(r"(?<![A-Za-z0-9])(?:" + "|".join(cased) + r")(?![A-Za-z0-9])")
    return re.compile("|".join(parts))


APP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(_pattern(slug, name) for slug, name, _ in CONNECTOR_POOL)


def named_apps(text: str) -> set[int]:
    """Indexes of the pool apps the text names (by app name; ordinary-word names only when capitalised)."""
    return {index for index, pattern in enumerate(APP_PATTERNS) if pattern.search(text or "")}


def _exact(slug: str, name: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(form) for form in _forms(slug, name) if form != slug or form == name) + r")(?![A-Za-z0-9])")


APP_EXACT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(_exact(slug, name) for slug, name, _ in CONNECTOR_POOL)


def names_app_as_written(text: str) -> bool:
    """The text writes a pool app's name in its own letter case ("Linear", not "linear"), so an ordinary word in a question is not taken for the app."""
    return any(pattern.search(text or "") for pattern in APP_EXACT_PATTERNS)


# What a work app holds. "the Square initiative" names something called Square; "the Asana task" names a thing in the app.
APP_NOUN = re.compile(r"\s+(?:tasks?|issues?|tickets?|records?|pages?|deals?|docs?|documents?|files?|comments?|cards?|boards?|messages?|history|invoices?|responses?|components?|to-?dos?|prs?|pull requests?|merge requests?|pipeline|tracker|database|servers?|spaces?|workspace|account|items?|forms?|channels?)\b", re.I)


def names_app_as_a_place(text: str) -> bool:
    """A name written as the app's own, and not as "the <name> <something the app does not hold>", which is a thing that shares the app's name."""
    text = text or ""
    for pattern in APP_EXACT_PATTERNS:
        for found in pattern.finditer(text):
            before = text[: found.start()].rstrip().lower()
            if not (before == "the" or before.endswith(" the")) or APP_NOUN.match(text, found.end()):
                return True
    return False


def shown_tools(tools: list, text: str) -> list:
    """The catalog without the connector tools of apps the request does not name; every other tool is kept as sent."""
    named = named_apps(text)
    return [tool for tool in tools if tool.name not in TOOL_APP or TOOL_APP[tool.name] in named]

# Bench v18: each seed's menu holds 1,400 to 2,000 tools: the simulated surface, every toolkit of a pinned snapshot of real apps, and the
# first-party tools of the real workspace. A snapshot tool renders with one optional free-form argument and no schema of its own; the
# first-party tools outside the simulated surface keep their schemas but perform nothing here either. Neither kind is what any request
# asks for, so both are left out of every catalog the model sees, as the unlinked connectors are; the simulated surface is kept as sent.
V18_TOOLKIT_ARGUMENT = "optional request for the tool"
V18_FIRST_PARTY_EXTRA = frozenset("""add_partner_deal_update add_safety_rule create_partner_deal_blocker discord_list_channels discord_list_connections discord_read_messages discord_search_messages explore_subject_neighbors faircopy_get_profile faircopy_review_text get_ditto_code_quota get_openrouter_credits get_partner_brand_assets get_partner_crm_dashboard get_partner_deal get_partner_deal_activity get_partner_flow get_partner_guide get_partner_pipeline get_partner_template get_skill get_tool_approvals groupme_add_album_media groupme_create_album groupme_create_event groupme_create_poll groupme_delete_message groupme_download_attachment groupme_edit_message groupme_get_account groupme_get_album groupme_get_event groupme_get_group groupme_get_message groupme_get_operation_status groupme_get_poll groupme_get_send_operation groupme_list_albums groupme_list_chats groupme_list_connections groupme_list_events groupme_list_groups groupme_list_pins groupme_list_polls groupme_list_reaction_choices groupme_pin_message groupme_preview_availability_reminder groupme_react_message groupme_read_messages groupme_rsvp_event groupme_search_messages groupme_send_availability_reminder groupme_send_composed_message groupme_send_message groupme_unlike_message groupme_unpin_message groupme_vote_poll list_partner_deals list_safety_rules list_skills notify_me publish_artifact record_partner_deal_payment register_partner_lead remove_safety_rule remove_skill resolve_partner_deal_blocker save_artifact save_skill search_facebook search_instagram search_tiktok search_x set_partner_crm_manager set_partner_deal_commercials set_skill_enabled slack_personal_get_self slack_personal_get_send slack_personal_list_connections slack_personal_list_threads slack_personal_read_messages slack_personal_search_messages slack_personal_send_message slack_personal_verify_send submit_feedback teamsnap_create_event teamsnap_create_forum_post teamsnap_create_forum_topic teamsnap_create_location teamsnap_extend_event_series teamsnap_get_account teamsnap_get_event teamsnap_get_event_series teamsnap_get_write_operation teamsnap_list_connections teamsnap_list_events teamsnap_list_forum_posts teamsnap_list_forum_topics teamsnap_list_locations teamsnap_list_members teamsnap_list_teams teamsnap_update_event teamsnap_update_location telegram_get_saved_message telegram_get_saved_messages telegram_get_send_operation telegram_list_connections telegram_list_conversations telegram_read_messages telegram_search_messages telegram_send_message update_partner_deal update_partner_deal_blocker whatsapp_get_self_conversation whatsapp_get_send_operation whatsapp_list_connections whatsapp_list_conversations whatsapp_read_messages whatsapp_search_messages whatsapp_send_message whatsapp_verify_send""".split())


def bulk_tool(tool) -> bool:
    """A bench-18 menu entry outside the simulated surface: a snapshot toolkit tool (the one free-form argument) or a workspace first-party tool."""
    params = tool.parameters if isinstance(tool.parameters, dict) else {}
    props = params.get("properties") or {}
    if set(props) == {"input"} and isinstance(props.get("input"), dict) and props["input"].get("description") == V18_TOOLKIT_ARGUMENT:
        return True
    return tool.name in V18_FIRST_PARTY_EXTRA


def surface_tools(tools: list) -> list:
    """The catalog without its bench-18 bulk; a catalog with none is returned as sent."""
    return [tool for tool in tools if not bulk_tool(tool)]
