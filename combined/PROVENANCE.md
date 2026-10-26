# Provenance

`combined/` is dan0l v24's released source (agent ecf5a1a2, sha256 f0fceb0c…, released
2026-10-25 05:29 UTC; `released/dan0l-v24_ecf5a1a2/release.json`) with our routing and record
selection put in place of its own:

- `app/ours/` holds our harness's router (`lane.py`, `meaning.py`, `intents.tsv`, `words.txt`)
  from `harness/app/routing/` on branch harness/hades-v6-base.
- `app/agent.py` routes with it (typo mending, own-records override, product questions,
  meaning router with guards) and refills both lanes' packets from the fused lexical,
  meaning and full-text orders; the contact-detail topic gate is ours.
- `app/packet.py` gains `fused_rank` and `refill`; `app/records.py` refills after building.

Everything else, the prompt loops of both lanes included, is dan0l's code unchanged.
