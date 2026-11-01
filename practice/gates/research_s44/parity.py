import sys, random, collections
sys.path.insert(0, '/home/bittensor/ditto/practice/gates')
import v14_oracle as o

CT = o.CHAIN_TEMPLATES

def plan(seed, domain, group, maxv):
    fit = [n for n, v in CT if v <= maxv]
    t = fit[o.v13_index(seed, f"v14-chain-{domain}-{group}", len(fit))]
    c = {2: "free", 3: "misplaced"}.get(o.v13_index(seed, f"v14-cue-{domain}-{group}", 4), "announced")
    u = o.v13_index(seed, f"v14-revert-unnamed-{domain}-{group}", 2) == 1
    return t, c, u

rng = random.Random(7)
for domain, maxv, groups in [("business", 4, [0, 1]), ("personal", 4, range(6)), ("personal", 3, range(6))]:
    cnt = collections.Counter()
    for _ in range(4000):
        s = rng.getrandbits(63)
        for g in groups:
            cnt[plan(s, domain, g, maxv)] += 1
    print(domain, maxv)
    for k, v in sorted(cnt.items()):
        print('   ', k, v)

# also: process/sequence/asof/membership detail distributions
cnt = collections.Counter()
for _ in range(3000):
    s = rng.getrandbits(63)
    for g in range(6):
        key = lambda name: f"v14-set-{name}-{g}"
        add = o.v14_coin(s, key("add")); noop = o.v14_coin(s, key("noop"))
        cnt[(add, noop)] += 1
print('membership add/noop', cnt)
cnt = collections.Counter()
for _ in range(3000):
    s = rng.getrandbits(63)
    g = 2
    key = lambda name: f"v14-proc-{name}-{g}"
    n = 3 + o.v13_index(s, key("n"), 3)
    mode = "untouched" if o.v14_coin(s, key("mode")) else "reopened"
    cnt[(mode, n)] += 1
print('process', sorted(cnt.items()))
cnt = collections.Counter()
for _ in range(3000):
    s = rng.getrandbits(63)
    cnt[o.business_family(s, 2)] += 1
    cnt['role:' + o.business_family(s, 3)] += 1
print('slots', cnt)
