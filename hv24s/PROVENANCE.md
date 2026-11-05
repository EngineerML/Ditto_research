# Provenance

## Base

This harness is built on **Hades v24**, a publicly released SN118 agent:

| | |
|---|---|
| Author | Hades (aceron) |
| Agent | a0fc00a9-580d-422b-9860-ed99b1124e9d |
| Artifact sha256 | 8a497b8e592396a5563c99422c7c8dc8a23d2920017be66b2413044d780e7625 |
| Finalized | 2026-11-02 19:25 UTC (bench 14) |
| Source released | 2026-11-04 22:18 UTC, through the platform's public artifact route after its embargo |

SN118 publishes a king's source once its embargo ends, and the subnet owner has confirmed that building on a released
agent is permitted. All of the design and almost all of the code here is Hades'. That includes its own lineage, from
dan0l v28 with ideas read in dan0l v30 and DrPresident v20, as its `DECLARATION.md` states. The MIT `LICENSE` ships
unchanged.

## What this revision changes

| File | Change | Size |
|---|---|---|
| `app/toolselect.py` | new: which listed tools a request is offered | 121 lines |
| `app/agent.py` | `CaseRunner.run` applies it when a request arrives and logs one line per case | 1 import, 6 lines |
| `DECLARATION.md` | one section added at the top; Hades' text below it is unchanged | about 15 lines |
| `PROVENANCE.md` | this file | new |

No routing rule, prompt, model setting, dependency or build file changes. To check, unpack both artifacts and run
`diff -r`: only the four files above differ.

## The change

A request keeps every general tool, plus the tools of each app it names. App tools of apps the request does not
mention are left out.
- An app-scoped tool is one whose own description names a brand that its own name starts with.
- Mail and calendar tools count as general: they are the assistant's own channels, and a request reaches them without
  naming an app.
- Kept tools are passed as supplied, in catalog order.

**Why:** bench 16 lists about 234 tools per request, and every call that carries them pays about 7,100 prompt tokens
for tools of apps the request never mentions. Offering about 31 cuts that to about 1,365 tokens a call, with no case losing
the tool it needed (100% recall over 10,000 served bench-16 tool cases).
