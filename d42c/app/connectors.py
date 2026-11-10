from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache

from .protocol import RunRequest, ToolDefinition

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


def listed_toolkits(req: RunRequest) -> RunRequest:
    """List toolkit actions only for a toolkit the message names; every other tool is listed as before."""
    grams = message_grams(req.user_input)
    kept = [tool for tool in req.tools if not TOOLKIT_ACTION.match(tool.name) or toolkit_named(tool.name, grams, req.user_input)]
    if len(kept) == len(req.tools):
        return req
    return req.model_copy(update={"tools": kept})
