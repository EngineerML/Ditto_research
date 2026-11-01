"""Live s45 progress: one line per 10 graded questions with score, program splits and conversational sanity.

Reads the running seed's scorer status (/v1/runs/<id> of the local subset scorer) every 15 s.
- score: running memory mean over graded questions;
- program: right / graded, twin groups split so far (shape oracle; enterprise groups not counted);
- sanity: pass rate of each slice (chitchat, declarative ack, behavior), the metric (their geometric mean) and
  the factor 0.25 + 0.75 x metric;
- est: memory mean x consistency factor (1 - 0.40 x splits / 13) x sanity factor."""
import glob
import json
import re
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict

sys.path.insert(0, "/home/bittensor/ditto/practice/gates")
from v14_oracle import shapes  # noqa: E402

SLICES = {"conversational-chitchat": 0.5, "conversational-declarative": 1.0, "declarative-behavior": 1.0}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
last = None
while True:
    runs = sorted(glob.glob("/home/bittensor/ditto/practice/2026*_ditto-harness-v8_full_rerun"))
    ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    port = re.search(r"dittobench-api-subset -port (\d+)", ps)
    ids = re.findall(r"GET /v1/runs/([0-9a-f-]+)", open(runs[-1] + "/scorer.log").read()) if runs else []
    if port and ids:
        try:
            d = json.load(opener.open(f"http://127.0.0.1:{port.group(1)}/v1/runs/{ids[-1]}", timeout=10))
        except Exception:  # noqa: BLE001
            d = {}
        part = d.get("partial") or []
        tens = len(part) // 10
        if part and (d.get("seed"), tens) != last and tens:
            last = (d.get("seed"), tens)
            seed = int(d["seed"])
            oracle = shapes(seed)
            mean = sum(c["score"] for c in part) / len(part)
            groups = defaultdict(list)
            prog = [c for c in part if c["case_id"] in oracle]
            for c in prog:
                s = oracle[c["case_id"]]
                if s.relation != "counterfactual":
                    groups[(s.domain, s.group)].append(c["score"] >= 0.5)
            splits = sum(1 for g in groups.values() if any(g) and not all(g))
            rates = []
            shown = []
            for cat, full in SLICES.items():
                got = [c["score"] >= full - 1e-9 for c in part if c["category"] == cat]
                if got:
                    rates.append(sum(got) / len(got))
                shown.append(f"{sum(got)}/{len(got)}")
            metric = 1.0
            for r in rates:
                metric *= r
            metric = metric ** (1 / len(rates)) if rates else 1.0
            sanity = 0.25 + 0.75 * metric
            est = mean * (1 - 0.40 * splits / 13) * sanity
            print(f"seed ..{str(seed)[-6:]} {len(part):3}/250 | score {mean:.3f} | program {sum(c['score'] >= 0.5 for c in prog)}/{len(prog)} "
                  f"splits {splits} | sanity {' '.join(shown)} factor {sanity:.3f} | est {est:.3f}", flush=True)
    try:
        if "all done" in open("/home/bittensor/ditto/practice/gates/run_s45.log").read():
            print("s45 all done", flush=True)
            break
    except OSError:
        pass
    time.sleep(15)
