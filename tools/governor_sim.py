import sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.governor import SpendGovernor


def cap(g, want):
    m = g.max_tokens(want)
    return want if m is None else m


# 175 datagen cases interleaved with 175 column cases; from case 60 on every column case is abusive: 4 calls x 9k
# prompt, each call reasoning to its output cap. Also a milder abuser (4 calls x 6k prompt, 6k output each).
for name, abusive in (("severe", (36000, 12000)), ("mild", (24000, 6000))):
    for label, use in (("no governor", False), ("governor", True)):
        g = SpendGovernor()
        spent = 0.0
        stopped = None
        for i in range(350):
            if i % 2 == 0:
                p, o = 14600, 2100
            elif i < 60:
                p, o = 2400, 500
            else:
                p, o = abusive[0], 4 * cap(g, abusive[1]) if use else 4 * abusive[1]
            spent += p * 70e-9 + o * 150e-9
            if spent > 1 and stopped is None:
                stopped = i
            if use:
                g.record(p, o)
        factor = 1.0 if spent <= 0.5 else max(0.3, 1.0 - (spent - 0.5) / 0.5 * 0.7)
        print(f"{name:7} {label:12} run cost ${min(spent, 1.0) if stopped else spent:.3f}  factor ~{factor:.2f}  " + (f"STOPPED at case {stopped}: {350 - stopped} cases score 0" if stopped else "completes"))
# ordinary run untouched
g = SpendGovernor()
for i in range(350):
    g.record(14600, 2100) if i % 2 == 0 else g.record(2400, 500)
print("ordinary run: lean", g.lean, "tight", g.tight)
