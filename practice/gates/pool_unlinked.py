#!/usr/bin/env python3
"""Every description the v15 connector pool can render (all tools, every variant), and the product/decoy catalog
strings, run through the lab copy's unlinked test (drp22v15/app/available.py).

    .venv/bin/python practice/gates/pool_unlinked.py
"""
import glob
import re
import sys

sys.path.insert(0, "/home/bittensor/ditto/drp22v15")
from app.available import UNLINKED

CATALOG = "/home/bittensor/ditto/repos/ditto-subnet/research/dittobench-datagen/catalog/"
src = open(CATALOG + "v15.go").read()
SUFFIX = " Needs the %s connector to be linked in Settings."
STR = r'"((?:[^"\\]|\\.)*)"'
app_re = re.compile(r'\{"([a-z0-9_]+)", "([^"]+)", \[\]connectorAction\{(.*?)\n\t\}\}', re.S)
ca_re = re.compile(r'ca\(([^)]*)\)')
total = missed = tools = 0
for slug, name, body in app_re.findall(src):
    for m in ca_re.finditer(body):
        args = re.findall(STR, m.group(1))
        key, does = args[0], args[3:]
        tools += 1
        for d in does:
            text = d.replace("%[1]s", name) + SUFFIX % name
            total += 1
            if not UNLINKED.search(text):
                missed += 1
                print("MISSED", slug + "_" + key, "|", text)
print(f"connector tools {tools}, descriptions {total}, missed {missed}")
hits = 0
for f in glob.glob(CATALOG + "*.go"):
    if f.endswith("v15.go") or f.endswith("_test.go"):
        continue
    for s in re.findall(r'"((?:[^"\\]|\\.){20,})"', open(f).read()):
        if UNLINKED.search(s):
            hits += 1
            print("PRODUCT/DECOY HIT", f.split("/")[-1], "|", s[:200])
print("product/decoy strings caught:", hits)
