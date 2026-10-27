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
