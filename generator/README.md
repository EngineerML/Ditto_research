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
go run ./cmd/challenge rehearse -dir /home/bittensor/ditto/generator \
  -hotkey 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY -seeds 3 -cases 80
```

`tools/generator_panel.py` runs the packs against one of our agent images with the official
challenge scorer (paid: OpenRouter) and prints solved/mean per family.
