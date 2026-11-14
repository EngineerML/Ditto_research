"""Simulate the c228 spend governor (app/governor.py) on run shapes measured locally, before any paid run.

Normal shape: the bench's order, 50 tool cases (measured on seed 1810006: about 21k prompt and 3.5k output per case for
the first 30, encounters included) then 125 memory cases (about 12k / 1.5k), then 175 generator column cases
(about 2.4k / 0.5k). Abusive shapes replace the column cases with costly ones. The governor must never act on the
normal shape and must keep every abusive shape under the $1.00 run budget.

    .venv/bin/python tools/governor_sim.py
"""
import sys

sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.governor import SpendGovernor  # noqa: E402

PROMPT, OUTPUT = 70e-9, 150e-9


def run(shape, use):
    g = SpendGovernor()
    spent, stopped, lean_at = 0.0, None, None
    for i, (p, o) in enumerate(shape):
        if use and g.lean:
            o = min(o, g.max_tokens(o) * 4)  # a case is about 4 calls; each is capped
        spent += p * PROMPT + o * OUTPUT
        if spent > 1 and stopped is None:
            stopped = i
        if use:
            g.record(p, o)
            if g.lean and lean_at is None:
                lean_at = i
    return spent, stopped, lean_at


normal = [(21400, 3470)] * 30 + [(17000, 1000)] * 20 + [(12000, 1500)] * 125 + [(2400, 500)] * 175
worst_order = [(21000, 3500)] * 50 + [(12000, 1500)] * 125 + [(2400, 500)] * 175
severe = normal[:175] + [(36000, 48000)] * 175
mild = normal[:175] + [(24000, 24000)] * 175
for name, shape in (("normal", normal), ("tool-heavy order", worst_order), ("severe abuse", severe), ("mild abuse", mild)):
    for label, use in (("no governor", False), ("governor", True)):
        spent, stopped, lean_at = run(shape, use)
        factor = 1.0 if spent <= 0.5 else max(0.3, 1.0 - (spent - 0.5) / 0.5 * 0.7)
        state = f"STOPPED at case {stopped} ({len(shape) - stopped} score 0)" if stopped else "completes"
        print(f"{name:17} {label:12} ${min(spent, 1.0):.3f} factor ~{factor:.2f} {state}" + (f", lean from case {lean_at}" if lean_at is not None else ""))
