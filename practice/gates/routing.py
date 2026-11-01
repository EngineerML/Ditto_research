"""Which program questions of v8 runs took the program path, and the lane/events of those that did not."""
import glob
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
SCOPE = re.compile(r"\bc[0-9a-f]{16}\b")
for run in sorted(glob.glob("/home/bittensor/ditto/practice/2026110*_ditto-harness-v8_full_rerun")):
    traces = [json.loads(line) for line in open(run + "/trace.jsonl")]
    prog = [t for t in traces if t["user_input"].startswith("Use only case file")]
    paths = Counter((t.get("path"), t.get("lane")) for t in prog)
    print(run[-50:], len(traces), "requests;", len(prog), "case-file questions;", dict(paths))
    for t in prog:
        if t.get("path") != "program":
            print("   ", t.get("lane"), "|", t["user_input"][:110], "|", [e for e in t.get("events") or []][:2])
