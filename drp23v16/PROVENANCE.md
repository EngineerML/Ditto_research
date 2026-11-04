# Provenance

## Base

This harness is built on **DrPresident v23**, a publicly released SN118 agent:

| | |
|---|---|
| Author | DrPresident |
| Agent | 8474358a-0592-40f6-8c70-4cec0212513c |
| Artifact sha256 | 9f3f21bc438352f690bb1e58994bdde02e032cd324e77e80a61a7d754eecfdeb |
| Finalized | 2026-10-31 (screened under policy v13, passed) |
| Source released | 2026-11-02 18:41 UTC, through the platform's public artifact route after its embargo |

SN118 publishes a king's source once its embargo ends, and the subnet owner has confirmed that building on a
released agent is permitted. All of the design and almost all of the code here is DrPresident's. DrPresident's own
lineage (v18 to v23) and the reading of every inherited part are in `DECLARATION.md`, which ships unchanged apart
from one section added at the top.

## What is inherited

29 of the 35 files in the v23 artifact are byte-identical to it. That covers almost the whole served path:
- lane routing (`app/lane.py`);
- the records, topic and program paths (`app/records.py`, `app/short.py`);
- memory and retrieval (`app/memory/` except one sentence of `deliberation.py`), the one-time final check;
- model settings, the `Dockerfile` and `requirements.txt`.

The action lane (`app/action.py`), the request hints (`app/thint.py`), the question-type hints (`app/qtype.py`) and
the decline sentence (`app/memory/deliberation.py`) are v23's with the small changes listed below.

DrPresident's own declaration rows describe this code, and they still apply word for word. Anything a reviewer finds
in those files is DrPresident's released and screened code, not a change made here.

## What this revision changes

| File | Change | Size |
|---|---|---|
| `app/available.py` | new: the unlinked-tool step described below | 55 lines |
| `app/agent.py` | `CaseRunner.run` calls that step before anything else, and logs one line per case | 1 import, 5 lines |
| `app/thint.py` | `product_tool` needs a capitalised word to name a product; `live_lookup` added (dan0l v30's live pattern) | 16 lines added, 3 changed |
| `app/action.py` | live lookups skip the result verdict and link note and run at low effort once looked up | 11 lines added, 5 changed |
| `app/qtype.py` | account-figure questions get the existing quantity hint; the direction hint asks for the calculate tool | 5 lines added, 1 changed |
| `app/memory/deliberation.py` | the decline sentence names what the checked records hold beyond the message's own words | 4 lines added, 1 changed |
| `DECLARATION.md` | one section added at the top, naming this base and the changes; DrPresident's text below it is unchanged | 12 lines |
| `PROVENANCE.md` | this file | new |

No routing rule, model setting, dependency or build file changes. To check, unpack both artifacts and run `diff -r`:
only the eight files above differ.

## Smaller changes (one row each in `DECLARATION.md`)

- **Product names.** v23 read any word one edit off a coined tool's name as that tool, so "right" read as the product
  "Rigut" and the host note asked for a call the message never named. A product is now named only by a capitalised
  word, the name itself or one slip off it when that word is not a real word. Over the served text of 200 generated
  bench-15 seeds (70,000 requests) product notes on a tool the request does not name fell from 71 to 4, and correct
  ones went from 1,998 to 2,000.
- **Live lookups**, taken from dan0l v30 (released): a request for what is current in the world, with no other request
  kind, skips the result verdict and the link note after a completed lookup and runs its later turns at low effort.
- **Grounded declines.** v23's decline sentence asked the model to name the records it checked "without repeating
  its contents", and the model often named only the person the message asked about. It now names them by a detail
  they give that the message does not (the full name behind a nickname, a role, city, relation or former workplace,
  the places or amounts a plan holds), and still repeats no address, handle or figure the message asks for.
- **Account figures.** Questions about a figure kept on an account and changed by later notes ("what is currently owed
  on X's account", "how many seats remain for X") had no question-type hint and were worked out in the head; they now
  get v23's own quantity hint, and the direction hint asks for the calculate tool too.

## The change: tools that need an unlinked connector

When a request arrives, a listed tool is left out of its catalog if its own description says, within one sentence,
that it needs or requires a connector, integration or connection to be linked, connected, set up or authorised (for
example "Needs the Asana connector to be linked in Settings.").

There is one exception. If the request's own text (its system text or the user's message) says in one sentence,
without negating it, that this app is linked or connected, the tool stays.

Lane routing and every menu the model sees then use the tools that remain. Each of them keeps its name,
description, schema and order. The model still chooses freely among them, including choosing no tool. The harness
log records per case how many tools were left out and how many stayed because the request said they were linked.

Why: such a tool cannot run in a workspace that has not linked it, and offering it puts unusable choices in front of
the model. Its everyday words also leak into the tool-name vocabulary that lane routing reads.

## Policy reading (policy v13)

- **W4, availability.** Availability may restrict a capability class, decided for the exact request and state. The
  availability source is the request's own tool description, which W10 makes authoritative, together with the public
  tool contract. `services/dittobench-api/PROTOCOL.md` says the catalog carries "unlinked connector tools" and that
  "the tool endpoint refuses every connector call with a 'not connected' error and performs nothing". The starter-kit
  README describes them as "connector tools the workspace has not linked".
- **I7.** No available capability is removed: a connector the request says is linked stays. The step makes no plan,
  no singleton and no forced call, and it never pins `tool_choice`.
- **W10.** Every tool that stays is passed exactly as supplied.
- **No benchmark trigger.** The step reads each tool's own description and the request's own words. It never uses a
  tool name, an app list, a seed or `bench_version`.

Where DrPresident's declaration says the whole catalog reaches the model, read it as the catalog after this step.
