package families

import (
	"fmt"

	"github.com/ditto-assistant/dittobench-datagen/challenge"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

// Family emits one case into the builder. i is the round and picks the
// variant.
//
// Every family here follows one idea: the gold value is stated plainly early
// on, and a later message points back at it without naming it ("back to the
// very beginning", "the same city as Q's party", "scrap the revert"). An
// agent that answers with the most recent value it can see is wrong, and one
// that cannot follow the pointer abstains. In v1 the families that restated
// or listed the value nearby (swaps, eliminations, picked suggestions) were
// solved 59 of 60 times by our own agent; the revert family was solved 13 of
// 20 times, and the misses were abstentions.
type Family func(b *Builder, i int) challenge.Case

// RevertToOriginal moves an event between cities two or three times, then
// sends it "back to the city we had in the very beginning".
func RevertToOriginal(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 1)[0]
	event := b.Any(events)
	c := b.Pick(cities, 2+i%2)
	first := moves(b, who, event, c)
	ev := b.Say(5, fmt.Sprintf("%s called. The %s is going back to the city we had in the very beginning.", who, event), "Back to the original plan then.")
	return cityCase("revert", i, who, event, c[0], c[1:], first[0], ev)
}

// RevertToPosition moves an event three or four times, then points back at a
// middle city by position or by counting changes: undo the last change; back
// to the second city; undo the last two changes.
func RevertToPosition(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 1)[0]
	event := b.Any(events)
	variant := i % 3
	n := 4
	if variant == 0 {
		n = 3
	}
	c := b.Pick(cities, n)
	said := moves(b, who, event, c)
	var line string
	switch variant {
	case 0:
		line = "%s undid the last change to the %s, so it's back where it was right before that."
	case 1:
		line = "%s wants the %s back in the second city it was planned for."
	default:
		line = "%s rolled back the last two changes to the %s."
	}
	ev := b.Say(5, fmt.Sprintf(line, who, event), "Understood, I'll update the plan.")
	var wrong []string
	for k, city := range c {
		if k != 1 {
			wrong = append(wrong, city)
		}
	}
	return cityCase("position", i, who, event, c[1], wrong, said[1], ev)
}

// SameAs moves one person's event to "the same city as" another person's
// event. Variant 1 moves the other event first, so only its latest city is
// right.
func SameAs(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 2)
	mine, theirs := b.Any(events), b.Any(events)
	for theirs == mine {
		theirs = b.Any(events)
	}
	c := b.Pick(cities, 2+i%2)
	gold := b.Say(0, fmt.Sprintf("%s's %s is booked in %s.", who[1], theirs, c[1]), fmt.Sprintf("%s, nice.", c[1]))
	if i%2 == 1 {
		gold = b.Say(2, fmt.Sprintf("%s moved the %s to %s.", who[1], theirs, c[2]), "Okay, noted.")
	}
	b.Say(1, fmt.Sprintf("%s's %s will be in %s.", who[0], mine, c[0]), fmt.Sprintf("%s sounds good.", c[0]))
	b.Filler()
	ev := b.Say(4, fmt.Sprintf("%s's %s is moving to the same city as %s's %s, so people can do both.", who[0], mine, who[1], theirs), "Smart, that saves everyone a trip.")
	answer, wrong := c[1], []string{c[0]}
	if i%2 == 1 {
		answer, wrong = c[2], []string{c[0], c[1]}
	}
	return cityCase("same-as", i, who[0], mine, answer, wrong, gold, ev)
}

// UndoRevert switches a party's welcome drink, reverts it to the original,
// then cancels the revert, so the switched drink stands.
func UndoRevert(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 1)[0]
	event := b.Any(events)
	d := b.Pick(drinksPool, 2)
	b.Say(0, fmt.Sprintf("The welcome drink at %s's %s is %s.", who, event, d[0]), "Good choice.")
	b.Filler()
	switched := b.Say(1, fmt.Sprintf("%s switched the welcome drink for the %s to %s.", who, event, d[1]), fmt.Sprintf("Okay, %s it is.", d[1]))
	b.Say(3, fmt.Sprintf("%s wants the %s drink back to what it was originally.", who, event), "Reverting it.")
	b.Filler()
	lines := []string{
		"%s changed their mind again about the %s drink: scrap going back, keep the switch.",
		"Forget what %s said about reverting the %s drink, the switch stays.",
	}
	ev := b.Say(5, fmt.Sprintf(lines[i%2], who, event), "Got it, keeping the switched drink.")
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("undo-revert-%d", i),
			QuestionType:      "knowledge-update",
			Question:          fmt.Sprintf("What is the welcome drink at %s's %s now?", who, event),
			ExpectedAnswer:    d[1],
			DistractorAnswers: []string{d[0]},
		},
		EvidencePairIDs: []string{switched, ev},
	}
}

// moves states an event's city and then each later city in its own wave, with
// filler in between, and returns the pair IDs in order.
func moves(b *Builder, who, event string, c []string) []string {
	ids := []string{b.Say(0, fmt.Sprintf("%s's %s is going to be in %s.", who, event, c[0]), fmt.Sprintf("Nice, %s should be a good spot.", c[0]))}
	lines := []string{
		"Update on %s's %s: it moved to %s.",
		"%s's %s changed again, it's %s now.",
		"Another change for %s's %s, now it's %s.",
	}
	for k, city := range c[1:] {
		b.Filler()
		ids = append(ids, b.Say(k+1, fmt.Sprintf(lines[k], who, event, city), fmt.Sprintf("Got it, %s now.", city)))
	}
	return ids
}

func cityCase(kind string, i int, who, event, gold string, distractors []string, evidence ...string) challenge.Case {
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("%s-%d", kind, i),
			QuestionType:      "knowledge-update",
			Question:          fmt.Sprintf("Which city is %s's %s in now?", who, event),
			ExpectedAnswer:    gold,
			DistractorAnswers: distractors,
		},
		EvidencePairIDs: evidence,
	}
}

// Default is the family rotation.
var Default = []Family{RevertToOriginal, RevertToPosition, SameAs, UndoRevert}
