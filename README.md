# Ditto (SN118) research

Workspace for inspecting Bittensor subnet 118 (Ditto): an agent-memory harness competition.

## Layout

```
docs/official/     snapshots of the official mining docs (heyditto.ai/docs/*.md), dated in each file
notes/             our findings, one dated file per check
live/YYYY-MM-DD/   raw JSON from the public platform API (leaderboard, bench config, fee quote, ...)
tools/             scripts that produce live/ and summarize it
repos/             (ignored) upstream clones from github.com/ditto-assistant
  ditto-subnet/      the monorepo: miners, validator, platform, scorer, datagen
  ditto-harness/     the Rust agent + memory library the reference harness uses
  turbobt/, bittensor-pylon/   chain tooling used by the validator
  archive/           repos archived on 2026-08-11 when everything moved into ditto-subnet
```

## Refresh

```bash
bash tools/fetch_live.sh            # writes live/<today>/
python3 tools/summarize.py live/<today>
```

Both go through the normal proxy environment of this machine. Chain queries use `btcli`
(aliased through proxychains on this machine).
