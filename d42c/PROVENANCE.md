# Provenance

## Base
This harness is the publicly released dan0l v42 (agent `e6959038-555c-4a49-a3e2-5377d020e79c`, archive sha256
`06c2aab9e00f72044ee7c8c22ace99676963d70f622232bbd113a9347a2a92dd`), published by the subnet on 2026-11-07 17:31 UTC.
Building on a released agent is permitted. `DECLARATION.md` is dan0l v42's own declaration, kept as shipped, with our
changes in a section at the top.

## Changes from dan0l v42
113 lines added and 13 removed, in 6 files under `app/`.

| Change | Files | Lines |
|---|---|---|
| Tool offer: the connector step lists tools instead of removing them. Every supplied tool stays callable and executable in both lanes. A tool the case reaches (called, or named in a tool result such as a tool search) is listed from the next turn on. Memory tools are always listed. | `app/offer.py` (new), `app/agent.py`, `app/surface.py`, `app/records.py`, `app/tools.py` | +74 / −5 |
| Records lane cost: no follow-up question (and so no rewrite turn); 2 search passes instead of 5 (identifier packets 2 instead of 6). The alias pass and the final check are unchanged. | `app/config.py`, `app/records.py`, `app/agent.py` | +39 / −8 |

Tuning fields can be overridden with `HARNESS_<FIELD>` environment variables for local practice. Nothing on the served
path sets them, so the defaults above are what runs.

## Layout
`app/` is formatted with ruff (79 columns, single quotes). Every file parses to the same Python AST as our working
tree, so the formatting changes no behaviour. The line references in dan0l v42's declaration below point to the
original layout of the released archive named above.

## Licence and attribution
The code is dan0l's, as released by the subnet, with the changes listed above.
