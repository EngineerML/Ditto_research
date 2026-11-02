"""How many tools the lab copy kept and left out on each request of a run, from its harness log.

    python3 practice/gates/check_unlinked.py RUN [V14_RUN]

With a v14 run of the same seed, the kept count is checked against the v14 catalog size: the unlinked test must
leave out the connectors and nothing else (no product tool, decoy or memory tool). Newer builds also log how many
connectors stayed because the request said their app is linked; on the bench that must stay 0."""
import json
import re
import sys
from collections import Counter

LINE = re.compile(r"case=(\S+) catalog: (\d+) tools kept, (\d+) unlinked left out(?:, (\d+) kept as linked by the request)?")

cases = [json.loads(line) for line in open(sys.argv[1] + "/trace.jsonl")]
logged = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in LINE.finditer(open(sys.argv[1] + "/harness.log").read())}
stayed = Counter(int(m.group(4) or 0) for m in LINE.finditer(open(sys.argv[1] + "/harness.log").read()))
counts = Counter(logged.get(case["case_id"]) for case in cases)
print(f"{len(cases)} requests; (kept, left out): {dict(counts)}; kept as linked by the request: {dict(stayed)}")
if len(sys.argv) > 2:
    sizes = Counter(len(case.get("tools") or []) for case in (json.loads(line) for line in open(sys.argv[2] + "/trace.jsonl")))
    print(f"v14 catalog sizes on the same seed: {dict(sizes)}")
    kept = {pair[0] for pair in counts if pair}
    print("kept equals the v14 catalog on every request:", kept == set(sizes) and None not in counts)
