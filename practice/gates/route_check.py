"""Run v8's routing checks on the three rewordings of one program question (no model calls)."""
import glob
import json
import sys

sys.path.insert(0, "/home/bittensor/ditto/v8")
from app.lane import classify, main_clause, own_records_question  # noqa: E402
from app.protocol import ToolDefinition  # noqa: E402

run = sorted(glob.glob("/home/bittensor/ditto/practice/2026110*_ditto-harness-v8_full_rerun"))[-1]
token = sys.argv[1]
for line in open(run + "/trace.jsonl"):
    t = json.loads(line)
    if token not in t["user_input"]:
        continue
    tools = [ToolDefinition(name=name) for name in t.get("tools") or []]
    lane = classify(main_clause(t["user_input"]), tools)
    print(f"path={t.get('path'):8} traced lane={t.get('lane')}")
    print(f"   Q: {t['user_input']}")
    print(f"   classify: {lane}  own_records_question(carried)={own_records_question(t['user_input'], tools, carried=True)}  "
          f"own_records_question={own_records_question(t['user_input'], tools)}")
