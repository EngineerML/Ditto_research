# Horizon's tool misses and the act-or-reply fix (2026-10-27)

Horizon (agent d5f819e9, the v3 phrase-table design) scored tool 0.92 / 0.85 / 0.94 on its three
official seeds. The official case results (public `/agent/{id}/scores`, per case: category, score,
grader notes; no case ids, not in dataset order) were matched to questions by category where a
seed has one question of it (practice/guide_fix/official_tool_misses.txt). Repeated official
misses: multi_web_read 3/3 seeds, v13_mutation_follow_up_read 3/3, discovery_font_set,
capability_discovery, code_compute, setting checks, contact-research email. Many had empty grader
notes: no tool call was seen at all.

## Local replay of the 0.85 seed (3126988865203959995), horizon's exact code

Tool 0.920 locally (platform providers, one run) against 0.85 official: same kinds of misses, so
the gap is mostly run-to-run and provider variance. The traces show one general fault, not a
phrasing one: the model answers in words instead of calling, although its own two reply drafts
made the call, and the last check then lets it stand:

| request | drafts | reply check | outcome |
|---|---|---|---|
| Make the app dark mode. | a call | REPLY | refused, citing an older "follow system" note |
| normalize 312, 12 and 310 ... one-off calculation | a call | REPLY | worked it out in its head |
| Set the accent to my rotal-ish one ... | a call | "NAME" (misread verdict) | wrote out a plan instead of calling |
| How do I manage which tools you're allowed to use ... | a call | ACT | answered from its own knowledge; the tool-search note had fired |

## Changes (tool4)

- Reply check: the verdict is the first ACT or REPLY anywhere in its answer, not its first word.
- Drafts note: says the reply makes no call, how many of the drafts made one, and that a call is
  how a requested action gets done. The model still decides (screening I3).
- Lane prompt: what the message tells you to do now is the current instruction; an older
  preference in the notes does not stop it, only a note that the user has not decided does.
- Notes: "how do I manage / where do I find ..." is a capability question, not a tool search;
  a correction updates the kind of note the message names. Three older false fires on new seeds'
  memory questions guarded ("Wihch email is current", "keep my workspace on system mode", "check
  what's changed since my old notes"). Over eight seeds no memory question gets a note.

## A/B, tool questions, platform providers, one run each ($0.65)

| seed | horizon | tool4 | gains / losses |
|---|---|---|---|
| 3126988865203959995 (the 0.85 seed, diagnosed on) | 0.920 | 0.940 | 5 / 3 |
| 138287359920490853 (fresh) | 0.930 | 0.953 | 4 / 2 |

Gains are the targeted failures (settings, capability, code compute, theme, memory update,
calendar create, multi-web read, agent jobs). The losses carry no misread verdict or misfired
note: a font set that stopped to ask, a setting check that reported instead of setting, a wrong
recipient address, two runs of one agreed-work question that skipped a create.

## v2 rejected under I3; v3fix (neutral note) measured (2026-10-27)

horizon v2 (12547cb) was rejected by screening policy v13, L2 and L3: "I3 model dissent: a valid
no-call model answer is not shipped when separate draft models propose catalog calls"
(action.py:534, 604, 608). The machinery is dan0l's; the rejected part was the note's wording
("Your reply above makes no call", "2 of 2 drafts", "a call is how it gets done"). b25920e puts
dan0l v25's note back, keeping the guidance edits, the action-lane sentence and the ReplyCheck parse.

Tool questions of seed 3126988865203959995 (100, platform providers):

| Run | Tool |
|---|---|
| horizon v1 | 0.920 |
| tool4 (rejected note) | 0.940 |
| v3fix | 0.880 |

Of the 14 questions that differ, capability_discovery, settings and code_compute_not_agent_job
were solved only by tool4: that is what the rejected note bought (about 0.03). A recheck (two more
runs) of the five v3fix lost that both others solved: contact_research_email and memory_delete 2/2
(noise), declarative_preference 1/2, code_compute and state_dependent_email 0/2. In both of those
the model kept a no-call reply through the neutral drafts note and the reply check. Adjusted for
the noise, v3fix is about 0.90, level with horizon v1: no tool gain left worth a resubmission.

## Pre-answer notes v4b..v4d on held-out seeds (2026-10-27)

All 100 tool questions, platform providers. 3126 and 138 were seen while tuning; the last two
seeds were not.

| Seed | horizon v1 | v4b | v4d |
|---|---|---|---|
| 3126988865203959995 (tuned) | 0.920 | 0.951 | |
| 138287359920490853 (tuned) | 0.930 | 0.929 | |
| 7019583318866023713 (held out) | 0.948 | 0.928 | |
| 5274190036118427761 (held out) | | | 0.915 |

The gains on the tuned seeds did not carry over; on held-out seeds the v4 line is level with v1
or below it, inside the run-to-run noise of about 0.03. One real, general fix stands: when a tool
result does not hold the field asked for, give what it says about the named thing (decoy add-on
questions 30/30 for v4d against 29/30 for v1 and 26/30 for v4b). Of v4d's eight misses on seed
5274..., one is ours (the sharper listed-option wording chose "navy" over the "blue variant");
the others are notes and lanes v1 shares (agreed-work routing x2, send-to-them, setting check,
effort clarification without the slot name, the records-lane web loop, the follow-up read
artifact).
