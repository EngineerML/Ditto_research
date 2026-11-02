"""Which v15 connector tool, added to the v14 catalog one at a time, moves a question out of DrPresident v22's records lane.

    .venv/bin/python practice/gates/route_culprit.py V14_RUN V15_RUN QUESTION [QUESTION ...]"""
import json
import sys

sys.path.insert(0, "/home/bittensor/ditto/released/DrPresident-v22_eeb26552/src")
from app.config import Levers  # noqa: E402
from app.lane import classify  # noqa: E402
from app.protocol import ToolDefinition  # noqa: E402
from app.thint import request_kind, tool_kind  # noqa: E402

v14 = [json.loads(line) for line in open(sys.argv[1] + "/trace.jsonl")]
v15 = [json.loads(line) for line in open(sys.argv[2] + "/trace.jsonl")]
t14 = v14[0]["tools"]
t15 = v15[0]["tools"]
extra = [n for n in t15 if n not in t14]
print(len(t14), "v14 tools;", len(extra), "added in v15")
levers = Levers.from_env()


def lane(q, names):
    tools = [ToolDefinition(name=n) for n in names]
    ln = classify(q, tools, levers.typo_cues, preamble=levers.route_preamble, asking=levers.route_asking, anchor=levers.route_anchor,
                  lexicon=levers.route_lexicon, operands=levers.route_operands, save=levers.route_save)
    return f"{ln.name}:{ln.reason} tool_kind={tool_kind(q, names)} request_kind={request_kind(q, names)}"


for q in sys.argv[3:]:
    print("\nQ:", q)
    print("  v14 catalog:", lane(q, t14))
    print("  v15 catalog:", lane(q, t15))
    base = lane(q, t14)
    hits = [n for n in extra if lane(q, t14 + [n]) != base]
    print("  single added tools that change it:", hits[:12])
