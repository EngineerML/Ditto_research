"""Deferred-tool check (no model): the listed tools equal the selector's choice, and every supplied tool stays callable.

    docker run --rm -v $DITTO/.cache/served16:/served:ro -v $DITTO/v16_atlas:/atlas:ro IMAGE python /atlas/offer_check.py 40
"""
import glob
import json
import sys

sys.path.insert(0, "/srv")
from app.protocol import ToolDefinition  # noqa: E402
from app.records import host_catalog  # noqa: E402
from app.surface import Surface  # noqa: E402
from app.toolselect import OFFER, Offer, select  # noqa: E402

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
same = differ = total = 0
for path in sorted(glob.glob("/served/v16_s*.json"))[:limit]:
    d = json.load(open(path))
    catalog = [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in d["catalog"]]
    for text in [c["prompt"] for c in d["tool_cases"]] + [c["question"] for c in d["memory_cases"]]:
        total += 1
        chosen, _ = select([{"name": t.name, "description": t.description} for t in catalog], text)
        listed = [t for t in catalog if t.name in set(chosen)]
        before = [x["function"]["name"] for x in Surface(listed, text).visible()]  # T1: no Offer set
        token = OFFER.set(Offer(catalog, chosen))
        surface = Surface(listed, text)
        now = [x["function"]["name"] for x in surface.visible()]
        if now == before:
            same += 1
        else:
            differ += 1
        deferred = [t.name for t in catalog if t.name not in set(chosen)]
        assert all(surface.knows(n) for n in deferred), "a deferred tool is not callable"
        assert set(deferred) <= set(host_catalog(listed)), "records lane does not know a deferred tool"
        OFFER.reset(token)
print(f"{total} requests: listed tools same as T1 {same}, different {differ}; every deferred tool callable in both lanes")

# The escape hatch: a deferred tool named by a tool result (as search_tools returns) is listed from the next turn on.
d = json.load(open(sorted(glob.glob("/served/v16_s*.json"))[0]))
catalog = [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in d["catalog"]]
text = "Post the release note to the team."
chosen, _ = select([{"name": t.name, "description": t.description} for t in catalog], text)
deferred = next(t.name for t in catalog if t.name not in set(chosen))
token = OFFER.set(Offer(catalog, chosen))
surface = Surface([t for t in catalog if t.name in set(chosen)], text)
n0 = len(surface.visible())
OFFER.get().reach("search_tools", json.dumps({"tools": [deferred]}))
names = [x["function"]["name"] for x in surface.visible()]
print(f"escape hatch: listed {n0} -> {len(names)} after search_tools named {deferred}; listed now: {deferred in names}; schema kept: {bool(surface.schema(deferred))}")
OFFER.reset(token)
