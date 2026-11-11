from __future__ import annotations

import math
import re
from collections.abc import Iterable
from functools import lru_cache

from .protocol import MEMORY_TOOL_NAMES, RunRequest, ToolDefinition

CONNECTOR_MARKER = re.compile(r"\bNeeds the (\S.{0,80}?) connector to be linked in Settings\.?\s*$")
APP_NAMES = {
    "slack": "Slack", "notion": "Notion", "linear": "Linear", "jira": "Jira", "github": "GitHub", "gitlab": "GitLab", "asana": "Asana", "trello": "Trello",
    "clickup": "ClickUp", "monday": "monday.com", "airtable": "Airtable", "confluence": "Confluence", "figma": "Figma", "salesforce": "Salesforce", "hubspot": "HubSpot", "pipedrive": "Pipedrive",
    "zendesk": "Zendesk", "intercom": "Intercom", "freshdesk": "Freshdesk", "stripe": "Stripe", "shopify": "Shopify", "quickbooks": "QuickBooks", "xero": "Xero", "dropbox": "Dropbox",
    "box": "Box", "onedrive": "OneDrive", "googledrive": "Google Drive", "sheets": "Google Sheets", "excel": "Excel Online", "teams": "Microsoft Teams", "discord": "Discord", "zoom": "Zoom",
    "sentry": "Sentry", "pagerduty": "PagerDuty", "datadog": "Datadog", "vercel": "Vercel", "netlify": "Netlify", "cloudflare": "Cloudflare", "aws": "AWS", "twilio": "Twilio",
    "docusign": "DocuSign", "greenhouse": "Greenhouse", "workday": "Workday", "gusto": "Gusto", "spotify": "Spotify", "strava": "Strava", "uber": "Uber", "doordash": "DoorDash",
    "instacart": "Instacart", "opentable": "OpenTable", "airbnb": "Airbnb", "reddit": "Reddit", "linkedin": "LinkedIn", "mixpanel": "Mixpanel", "amplitude": "Amplitude", "snowflake": "Snowflake",
    "bigquery": "BigQuery", "postgres": "Postgres", "webflow": "Webflow", "wordpress": "WordPress", "typeform": "Typeform", "1password": "1Password", "okta": "Okta", "basecamp": "Basecamp",
    "smartsheet": "Smartsheet", "miro": "Miro", "loom": "Loom", "gong": "Gong", "outreach": "Outreach", "marketo": "Marketo", "segment": "Segment", "looker": "Looker",
    "tableau": "Tableau", "metabase": "Metabase", "databricks": "Databricks", "mongodb": "MongoDB Atlas", "supabase": "Supabase", "firebase": "Firebase", "heroku": "Heroku", "digitalocean": "DigitalOcean",
    "azure": "Azure", "gcp": "Google Cloud", "kubernetes": "Kubernetes", "terraform": "Terraform Cloud", "circleci": "CircleCI", "bitbucket": "Bitbucket", "grafana": "Grafana", "statuspage": "Statuspage",
    "opsgenie": "Opsgenie", "brex": "Brex", "ramp": "Ramp", "expensify": "Expensify", "paypal": "PayPal", "square": "Square", "plaid": "Plaid", "etsy": "Etsy",
    "amazon_seller": "Amazon Seller Central", "ups": "UPS", "fedex": "FedEx", "canvas_lms": "Canvas LMS", "duolingo": "Duolingo", "peloton": "Peloton", "fitbit": "Fitbit", "myfitnesspal": "MyFitnessPal",
    "goodreads": "Goodreads", "letterboxd": "Letterboxd", "steam": "Steam", "twitch": "Twitch", "sonos": "Sonos", "philips_hue": "Philips Hue", "nest": "Nest", "ring": "Ring",
    "tesla": "Tesla", "lyft": "Lyft", "expedia": "Expedia", "tripit": "TripIt", "zapier": "Zapier", "ifttt": "IFTTT", "mailgun": "Mailgun", "sendgrid": "SendGrid",
    "bamboohr": "BambooHR", "lever": "Lever", "rippling": "Rippling", "vanta": "Vanta", "snyk": "Snyk", "postman": "Postman", "readwise": "Readwise", "pocket": "Pocket",
    "evernote": "Evernote", "obsidian": "Obsidian Sync", "coda": "Coda", "quip": "Quip", "hootsuite": "Hootsuite", "buffer": "Buffer", "canny": "Canny", "productboard": "Productboard",
}
SLUGS_LONGEST_FIRST = sorted(APP_NAMES, key=len, reverse=True)


@lru_cache(maxsize=None)
def phrase_pattern(phrase: str) -> re.Pattern[str]:
    words = [re.escape(word) for word in phrase.split()]
    return re.compile(r"(?<![A-Za-z0-9])" + r"\s+".join(words) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def connector_slug(tool_name: str) -> str:
    return next((slug for slug in SLUGS_LONGEST_FIRST if tool_name.startswith(slug + "_")), "")


def app_of(tool: ToolDefinition) -> str:
    description = tool.description or ""
    marked = CONNECTOR_MARKER.search(description)
    if marked:
        return marked.group(1)
    slug = connector_slug(tool.name)
    if slug and mentions_app(description, APP_NAMES[slug]):
        return APP_NAMES[slug]
    return ""


def names_app(message: str, app: str) -> bool:
    return any((app.islower() or not match.group(0).islower()) and not NAME_CONTINUES.match(message, match.end()) for match in phrase_pattern(app).finditer(message))


def named_app_tools(message: str, tool_names: Iterable[str]) -> dict[str, list[str]]:
    named: dict[str, list[str]] = {}
    for name in tool_names:
        slug = connector_slug(name)
        if slug and names_app(message, APP_NAMES[slug]):
            named.setdefault(APP_NAMES[slug], []).append(name)
    return named


def linked_tools(req: RunRequest) -> RunRequest:
    apps = {tool.name: app_of(tool) for tool in req.tools}
    named = {app for app in set(apps.values()) if app and names_app(req.user_input, app)}
    kept = [tool for tool in req.tools if not apps[tool.name] or apps[tool.name] in named]
    if len(kept) == len(req.tools):
        return req
    return req.model_copy(update={"tools": kept})


NAME_CONTINUES = re.compile(r"\s+[A-Z][a-z]")


def mentions_app(text: str, app: str) -> bool:
    return any(app.islower() or not match.group(0).islower() for match in phrase_pattern(app).finditer(text))

# Toolkit actions (bench 18 menus carry 1,400-2,000 of them, ``ZOOM_CREATE_PROJECT``): third-party catalog entries
# named in upper case with underscores. They stay callable (app/offer.py); the menu lists one only when the message
# names it or its toolkit ("Zoom", "Digital Ocean"), and a tool the case reaches is listed from the next turn on.
TOOLKIT_ACTION = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
TOOLKIT_PREFIX_WORDS = 3


def message_grams(message: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", message.lower())
    return {"_".join(words[i:i + k]) for k in range(1, TOOLKIT_PREFIX_WORDS + 1) for i in range(len(words) - k + 1)} | {"".join(words[i:i + k]) for k in range(2, TOOLKIT_PREFIX_WORDS + 1) for i in range(len(words) - k + 1)}


def toolkit_named(name: str, grams: set[str], message: str) -> bool:
    if name in message:
        return True
    parts = name.lower().split("_")
    prefixes = {"_".join(parts[:k]) for k in range(1, min(TOOLKIT_PREFIX_WORDS, len(parts) - 1) + 1)}
    prefixes |= {"".join(parts[:k]) for k in range(2, min(TOOLKIT_PREFIX_WORDS, len(parts) - 1) + 1)}
    return any(len(prefix) >= 3 and prefix in grams for prefix in prefixes)


MENU_UNTOUCHED = 60
MENU_SIZE = 40
NAMED_FIRST = 1000.0
# Always listed on a trimmed menu: the memory tools (the recall turn reads them from the listed menu), the tools that
# save, change or delete a memory, and the product's core capabilities (web, links, code, email, calendar, workflows
# and jobs, images, artifacts, tool discovery).
CORE_TOOLS = MEMORY_TOOL_NAMES | frozenset({
    "save_memory", "update_memory", "delete_memory", "search_web", "read_links", "run_code", "search_tools", "discover_capabilities", "gmail_send", "calendar_create_event",
    "calendar_search_events", "create_workflow", "list_workflows", "run_workflow", "list_schedules", "list_agent_jobs",
    "execute_agent_job", "create_image", "edit_image", "artifacts",
})
MENU_STOP = frozenset("a an the and or of to in on at for with my me you your is are be it this that from by as please can could would will do does what which who when how about into up out new all any some".split())


def menu_words(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in MENU_STOP]


def listed_toolkits(req: RunRequest) -> RunRequest:
    """List a menu the size of a pre-v18 one; every supplied tool stays callable (app/offer.py).

    A menu of at most MENU_UNTOUCHED tools is listed as it is. A larger one (bench 18 sends 1,400-2,000 tools) lists
    the core tools, the tools of an app or toolkit the message names, and then the tools whose names and
    descriptions share the most distinctive words with the message, up to MENU_SIZE. Toolkit actions the message does
    not name are never listed. A tool the case reaches (called, or named by a tool result) is listed from the next
    turn on, and memory tools are always listed."""
    grams = message_grams(req.user_input)
    tools = [tool for tool in req.tools if not TOOLKIT_ACTION.match(tool.name) or toolkit_named(tool.name, grams, req.user_input)]
    if len(tools) <= MENU_UNTOUCHED:
        return req if len(tools) == len(req.tools) else req.model_copy(update={"tools": tools})
    asked = set(menu_words(req.user_input))
    texts = {tool.name: (set(menu_words(tool.name.replace("_", " "))), set(menu_words(tool.description or ""))) for tool in tools}
    seen: dict[str, int] = {}
    for name_words, description_words in texts.values():
        for word in name_words | description_words:
            seen[word] = seen.get(word, 0) + 1
    rarity = {word: math.log(len(tools) / (1 + count)) for word, count in seen.items()}
    kept: list[ToolDefinition] = []
    ranked: list[tuple[float, int, ToolDefinition]] = []
    for position, tool in enumerate(tools):
        app = tool.name.split("_")[0].lower()
        if tool.name in CORE_TOOLS or tool.name in req.user_input:
            kept.append(tool)
            continue
        name_words, description_words = texts[tool.name]
        score = sum(rarity.get(word, 0.0) * (2.0 if word in name_words else 1.0) for word in asked & (name_words | description_words))
        # The tools of an app or toolkit the message names come first, best match first, within the same cap.
        if (len(app) >= 3 and app in grams and "_" in tool.name) or TOOLKIT_ACTION.match(tool.name):
            score += NAMED_FIRST
        if score > 0:
            ranked.append((-score, position, tool))
    ranked.sort(key=lambda item: (item[0], item[1]))
    chosen = {tool.name for tool in kept} | {tool.name for _, _, tool in ranked[:max(0, MENU_SIZE - len(kept))]}
    return req.model_copy(update={"tools": [tool for tool in tools if tool.name in chosen]})
