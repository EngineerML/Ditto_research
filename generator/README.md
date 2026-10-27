# Generator competition work

Our entry for SN118's generator competition: a deterministic Go program that writes memory
challenge packs the top agents split on. Rules, scoring and field evidence:
notes/2026-10-27_generator_competition.md.

Branch `generator`, cut from harness/dan0l-combined so the agent-side failure notes and tools
are at hand.

## Layout

The builder, the value pools and `main.go` come from the public starter kit
(`repos/ditto-subnet/miners/dittobench-generator-starter-kit`, MIT, see LICENSE.starter-kit).
The families are ours. The kit's own four families are dropped: they are 76/76 trivial in real
rounds, and repeating them would only collect duplicates.

All four families state the gold value plainly, then change what is true in a later message
that never names the value again:

| Family | What happens | Gold |
|---|---|---|
| `revert` | an event moves city two or three times, then "back to the very beginning" or "undo the last change" | the first, or the middle, city |
| `swapped` | two people's allergies, later "I had them the wrong way round" | the food first given for the other person |
| `picked` | two people suggest a city, later "we went with X's idea" (one variant: X revised their suggestion first) | the winner's latest city |
| `elimination` | three drinks shortlisted, two ruled out in separate messages | the one never ruled out |

Six waves, about 360 pairs at 80 cases; every family draws reserved names and values, so cases
in one pack never collide.

## Checks

```bash
cd generator && go vet ./... && go test ./...      # every size 8..80 validates on several seeds
cd repos/ditto-subnet/research/dittobench-datagen
go run ./cmd/challenge rehearse -dir ../../../../generator \
  -hotkey 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY -seeds 3 -cases 80
```

`tools/generator_panel.py` runs the packs against one of our agent images with the official
challenge scorer (paid: OpenRouter) and prints solved/mean per family.

## Results against our own agent (horizon v2 image, one seed, 80 cases)

| Version | Family | Solved |
|---|---|---|
| v1 | elimination / swapped / picked | 20/20, 20/20, 19/20 (trivial: replaced) |
| v1 | revert ("back to the very beginning" / "undo the last change") | 13/20 (misses are abstentions) |
| v2 | revert / position | 16/20, 16/20 |
| v2 | same-as / undo-revert | 20/20, 20/20 |

About $0.25 per 80-case run. One agent cannot show what is discriminating (that needs two
owners solving and at least one agent failing); the next step is a local panel of different
agents.
