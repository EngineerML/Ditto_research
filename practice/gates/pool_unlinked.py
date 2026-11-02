#!/usr/bin/env python3
"""Every description the v15 connector pool can render (all tools, every variant), and the product/decoy catalog
strings, run through the lab copy's unlinked test (drp22v15/app/available.py). Each connector must be caught with
its own app name, and a few request sentences check the "request says it is linked" exception.

    .venv/bin/python practice/gates/pool_unlinked.py [LAB_DIR]
"""
import glob
import re
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else "/home/bittensor/ditto/drp22v15")
from app.available import UNLINKED, needed_link, says_linked
from app.protocol import ToolDefinition

CATALOG = "/home/bittensor/ditto/repos/ditto-subnet/research/dittobench-datagen/catalog/"
src = open(CATALOG + "v15.go").read()
SUFFIX = " Needs the %s connector to be linked in Settings."
STR = r'"((?:[^"\\]|\\.)*)"'
app_re = re.compile(r'\{"([a-z0-9_]+)", "([^"]+)", \[\]connectorAction\{(.*?)\n\t\}\}', re.S)
ca_re = re.compile(r'ca\(([^)]*)\)')
total = missed = wrong_app = tools = 0
apps = set()
for slug, name, body in app_re.findall(src):
    apps.add(name)
    for m in ca_re.finditer(body):
        args = re.findall(STR, m.group(1))
        key, does = args[0], args[3:]
        tools += 1
        for d in does:
            text = d.replace("%[1]s", name) + SUFFIX % name
            total += 1
            app = needed_link(ToolDefinition(name=slug + "_" + key, description=text))
            if app is None:
                missed += 1
                print("MISSED", slug + "_" + key, "|", text)
            elif app != name:
                wrong_app += 1
                print("WRONG APP", repr(app), "for", name, "|", text)
print(f"connector tools {tools} ({len(apps)} apps), descriptions {total}, missed {missed}, wrong app {wrong_app}")
hits = 0
for f in glob.glob(CATALOG + "*.go"):
    if f.endswith("v15.go") or f.endswith("_test.go"):
        continue
    for s in re.findall(r'"((?:[^"\\]|\\.){20,})"', open(f).read()):
        if UNLINKED.search(s):
            hits += 1
            print("PRODUCT/DECOY HIT", f.split("/")[-1], "|", s[:200])
print("product/decoy strings caught:", hits)

SAMPLES = [
    ("Slack", "I linked Slack yesterday. Post the summary there.", True),
    ("Slack", "Slack is connected now, so send it to the team.", True),
    ("monday.com", "monday.com is connected to this workspace.", True),
    ("Slack", "Slack isn't connected yet. Just draft the message.", False),
    ("Slack", "Post the summary to Slack.", False),
    ("Slack", "I never linked Slack.", False),
    ("Slack", "My phone is connected. Message the team on Slack.", False),
    ("Notion", "I linked Notion. Slack is not connected.", True),
    ("Slack", "I linked Notion. Slack is not connected.", False),
]
bad = [(app, text, want) for app, text, want in SAMPLES if says_linked(app, text) != want]
for app, text, want in bad:
    print("SAMPLE WRONG", app, "|", text, "| want", want)
print(f"linked-by-request samples: {len(SAMPLES) - len(bad)} of {len(SAMPLES)} right")
