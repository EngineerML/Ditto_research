import json, sys, re
run, served_path, ds_path = sys.argv[1:4]
S = json.load(open(served_path)); D = json.load(open(ds_path))
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
CID = re.compile(r'\bc[0-9a-f]{16}\b')
norm = lambda s: CID.sub('<ID>', UUID.sub('<ID>', s))
st = {norm(t['prompt']) for t in S['tool_cases']} | {norm(m['question']) for m in S['memory_cases']}
dt = {norm(t['prompt']) for t in D['tool_cases']} | {norm(m['question']) for m in D['memory_cases']}
ins = ind = both = neither = 0; ids_in = 0; samples = []
for line in open(run + '/trace.jsonl'):
    o = json.loads(line)
    u = o.get('user_input')
    if u is None: continue
    if UUID.search(u): ids_in += 1
    a, b = norm(u) in st, norm(u) in dt
    ins += a; ind += b; both += a and b
    if not a and not b:
        neither += 1; samples.append(u[:160])
print(dict(served_match=ins, dataset_match=ind, both=both, neither=neither, with_uuid=ids_in))
for s in samples[:5]: print(' ', s)
# records: served wave pairs vs dataset wave pairs
sp = {p['pair_id']: p for w in S['memory_waves'] for p in (w['pairs'] or [])}
for t in S['tool_cases']:
    for p in (t['prerequisite_pairs'] or []): sp.setdefault(p['pair_id'], p)
dp = {p['pair_id']: p for w in D['memory_waves'] for p in (w.get('pairs') or [])}
for t in D['tool_cases']:
    for p in (t.get('prerequisite_pairs') or []): dp.setdefault(p['pair_id'], p)
same_p = sum(1 for k in dp if k in sp and sp[k]['prompt'] == dp[k]['prompt'])
same_r = sum(1 for k in dp if k in sp and sp[k]['response'] == dp[k]['response'])
print('pairs', len(dp), 'in served', sum(k in sp for k in dp), 'prompt identical', same_p, 'response identical', same_r)
