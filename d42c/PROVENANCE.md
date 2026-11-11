# Provenance

## Base
This harness is the publicly released dan0l v42 (agent `e6959038-555c-4a49-a3e2-5377d020e79c`, archive sha256
`06c2aab9e00f72044ee7c8c22ace99676963d70f622232bbd113a9347a2a92dd`), published by the subnet on 2026-11-07 17:31 UTC.
Building on a released agent is permitted. `DECLARATION.md` is dan0l v42's own declaration, kept as shipped, with our
changes in a section at the top.

## Changes from dan0l v42
511 lines added and 22 removed, in 12 files under `app/`.

| Change | Files | Lines |
|---|---|---|
| Tool offer: the connector step lists tools instead of removing them. Every supplied tool stays callable and executable in both lanes. A tool the case reaches (called, or named in a tool result such as a tool search) is listed from the next turn on. Memory tools are always listed. | `app/offer.py` (new), `app/agent.py`, `app/surface.py`, `app/records.py`, `app/tools.py` | +74 / −5 |
| Records lane cost: no follow-up question (and so no rewrite turn); 2 search passes instead of 5 (identifier packets 2 instead of 6). The final check is unchanged. | `app/config.py`, `app/records.py`, `app/agent.py` | +39 / −8 |
| Alias pass input: the pass reads only the packet records that mention an asked name, under the packet's own record marks. It keeps an alias only when one record holds both the alias and the asked name, so the other records could not change its result. The deciding call still reads the whole packet. | `app/records.py` (`RecordsEngine.alias_view`), `app/config.py`, `app/agent.py` | +19 / −4 |
| Name chain: for a person the message names by one first name, records that write that name with a surname and records that give another first name with the same surname (next to it, or in a naming sentence) are pinned into the packet with the other name's own records, and an advisory note names them by mark, unchecked, the records deciding. No model call; nothing is added when there is no such tie. | `app/memory/chain.py` (new), `app/records.py`, `app/config.py`, `app/agent.py` | +160 / −1 |
| Quoted sentences: the alias pass's note and the name-chain note also quote, newest first, the sentences of the user's own records that use the other name, each once (a sentence repeated under another lead-in counts once), at most six, each with its record's mark. A fact told in passing inside a longer message is then read next to the tie that makes it count. No model call; the records still decide. | `app/memory/chain.py` (`said_under`), `app/memory/aliases.py`, `app/records.py` | +44 / −1 |
| Large tool menus (bench 18 sends 1,400-2,000 tools): after the connector step, a menu of more than 60 tools lists at most 40: the memory tools and the core product tools (web, links, code, email, calendar, workflows and jobs, images, artifacts, tool discovery), then the tools of an app or toolkit the message names, then the best word matches to the message. Upper-case toolkit actions the message does not name are never listed. Every supplied tool stays callable through the tool offer, and a tool the case reaches is listed from the next turn on. A menu of 60 tools or fewer (every bench before 18) is listed as before. The tools that save, change or delete a memory are listed with the core tools. | `app/connectors.py` (`listed_toolkits`), `app/agent.py` | +83 / −6 |
| Action lane prompt: two more sentences. A result that says a job or run started, is running, pending or was retried is checked with the tool that reports it until that run (or its retry) has finished, before any figure from it is used; before creating an item, the results already returned are looked through for one that names the same identifier or title, and that item's reference is given instead. | `app/action.py` (`ACTION_LANE_PROMPT`) | +2 / −0 |
| Records lane reading rules: one more bullet. An event dated by its distance from another takes the calendar date that distance gives, and what came immediately before or after an event is found by putting the events of that subject in date order. | `app/records.py` (`READING_RULES`) | +1 / −0 |
| Event dates, program path: when the message asks what came immediately before or after an event, a note that dates something by its distance from another event ("13 days after the board review") gets a line giving the calendar date, worked out from the one note that dates the other event; the lines are headed as worked out by code, not checked, the notes deciding. No model call; nothing is added when no such note can be placed. | `app/memory/spans.py` (new), `app/short.py` | +93 / −1 |

Tuning fields can be overridden with `HARNESS_<FIELD>` environment variables for local practice. Nothing on the served
path sets them, so the defaults above are what runs.

## Layout
`app/` is formatted with ruff (88 columns, double quotes). Every file parses to the same Python AST as our working
tree, so the formatting changes no behaviour. The line references in dan0l v42's declaration below point to the
original layout of the released archive named above.

## Licence and attribution
The code is dan0l's, as released by the subnet, with the changes listed above.
