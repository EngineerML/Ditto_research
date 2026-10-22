# Released king source (2026-10-22)

## Policy

- Only kings are released. The exact submission must have held the crown, earned winner emissions
  in a completed tempo, reached the 3-validator score quorum, and then waited out the embargo from
  `emission_confirmed_at` (`apps/platform/docs/public-telemetry.md`).
- Live embargo: **24 hours** (`artifact_release.embargo_hours` on every submission). The repo docs
  still mention 48 h (default) and 120 h (revision 3, 2026-07-28); the live value wins.
- Building on a released agent is allowed: "the subnet owner has confirmed that building on a
  released miner agent is permitted" (`apps/platform/docs/anti-copy-reference.md`). Anti-copy
  signals against published code are withdrawn.
- Still flagged: copying anything inside its embargo, and a submission that matches an embargoed
  artifact more closely than any published one. Confirmed plagiarism can cost a hotkey ban.
- About 30 of ~1600 submissions have ever been released.

## State at 01:58 UTC

| agent | role | source |
|---|---|---|
| 82172ff9 blinkrazor v3 | earlier incumbent, bench v13, 0.7759 | released, downloaded to `released/blinkrazor-v3_82172ff9/` (sha256 40c4d54b...) |
| e6638d76 Hades v6 | current champion, 0.8043 | embargoed until 2026-10-22 07:53 UTC |
| 3e95c47b | | awaiting confirmed winner emissions |

blinkrazor v3 is a C++ rewrite, not the Rust starter kit: about 9,000 lines (agent loop, SQLite
store, retrieval, embeddings, prompts in `assets/*.json`), one Dockerfile that builds with cmake
and runs its smoke tests, serves port 8080, calls the model through the OpenRouter-compatible
endpoint (Ollama on localhost for local practice).

## How to fetch

```bash
bash tools/fetch_release.sh <agent_id> <label>   # verifies sha256, refuses unsafe tar members, never runs code
```

## Plan

Use Hades v6 as the base once it is released (current champion, +0.028 over blinkrazor v3),
compare it with blinkrazor v3, and put our own changes in a tracked folder. Remember the champion
defense: beating Hades needs about +0.033 composite, not just a higher number.
