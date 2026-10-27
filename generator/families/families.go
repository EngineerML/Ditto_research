package families

import (
	"fmt"

	"github.com/ditto-assistant/dittobench-datagen/challenge"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

// Family emits one case into the builder. i distinguishes repeated uses and
// picks the variant.
//
// Every family here follows one idea: the gold value is stated plainly early
// on, and a later message changes what is true without naming the value
// again. An agent that answers with the most recent value it can see is
// wrong; one that applies the later message to the earlier fact is right.
type Family func(b *Builder, i int) challenge.Case

// RevertToOriginal moves an event between cities and then undoes a change in
// words that name no city. Variants: two moves and "back to the first city";
// three moves and "back to the first city"; three moves and "undo the last
// change", whose answer is the middle city.
func RevertToOriginal(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 1)[0]
	event := b.Any(events)
	variant := i % 3
	n := 2
	if variant > 0 {
		n = 3
	}
	c := b.Pick(cities, n)
	first := b.Say(0, fmt.Sprintf("%s's %s is going to be in %s.", who, event, c[0]), fmt.Sprintf("Nice, %s should be a good spot.", c[0]))
	b.Filler()
	second := b.Say(2, fmt.Sprintf("Update on %s's %s: it moved to %s.", who, event, c[1]), fmt.Sprintf("Got it, %s now.", c[1]))
	if n == 3 {
		b.Say(3, fmt.Sprintf("%s's %s changed again, it's %s now.", who, event, c[2]), "Okay, noted the new city.")
	}
	b.Filler()
	if variant < 2 {
		ev := b.Say(4, fmt.Sprintf("%s called. The %s is going back to the city we had in the very beginning.", who, event), "Back to the original plan then.")
		return revertCase(i, who, event, c[0], c[1:], first, ev)
	}
	ev := b.Say(5, fmt.Sprintf("%s undid the last change to the %s, so it's back where it was right before that.", who, event), "Understood, reverting that one change.")
	return revertCase(i, who, event, c[1], []string{c[0], c[2]}, second, ev)
}

func revertCase(i int, who, event, gold string, distractors []string, evidence ...string) challenge.Case {
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("revert-%d", i),
			QuestionType:      "knowledge-update",
			Question:          fmt.Sprintf("Which city is %s's %s in now?", who, event),
			ExpectedAnswer:    gold,
			DistractorAnswers: distractors,
		},
		EvidencePairIDs: evidence,
	}
}

// SwappedPair states two people's allergies and later says they were the
// other way round, without repeating either food. The question asks about
// one of the two, so the answer is the food first stated for the other.
func SwappedPair(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 2)
	food := b.Pick(allergens, 2)
	event := b.Any(events)
	ev1 := b.Say(1, fmt.Sprintf("For the %s menu: %s is allergic to %s and %s to %s.", event, who[0], food[0], who[1], food[1]), "Thanks, I'll keep both in mind.")
	b.Filler()
	swaps := []string{
		"Correction on the %s menu: I had %s and %s the wrong way round, their allergies are swapped.",
		"I mixed up %[2]s and %[3]s for the %[1]s menu. Each one has the allergy I gave the other.",
	}
	ev2 := b.Say(4, fmt.Sprintf(swaps[i%2], event, who[0], who[1]), "Thanks for catching that, I've switched them.")
	ask, gold, other := who[1], food[0], food[1]
	if i%4 >= 2 {
		ask, gold, other = who[0], food[1], food[0]
	}
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("swapped-%d", i),
			QuestionType:      "knowledge-update",
			Question:          fmt.Sprintf("What is %s allergic to?", ask),
			ExpectedAnswer:    gold,
			DistractorAnswers: []string{other},
		},
		EvidencePairIDs: []string{ev1, ev2},
	}
}

// PickedSuggestion has two people suggest a city each, and a later message
// says whose suggestion won, by name only. Variants: the second suggester
// wins; the first wins; the second revises their suggestion before winning,
// so only their latest city counts.
func PickedSuggestion(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 2)
	event := b.Any(events)
	variant := i % 3
	n := 2
	if variant == 2 {
		n = 3
	}
	c := b.Pick(cities, n)
	ev1 := b.Say(0, fmt.Sprintf("Planning the %s with %s and %s. %s suggested %s.", event, who[0], who[1], who[0], c[0]), fmt.Sprintf("%s could work well.", c[0]))
	ev2 := b.Say(1, fmt.Sprintf("%s thinks %s would be better for the %s.", who[1], c[1], event), "Both sound like good options.")
	b.Filler()
	var gold string
	var evidence, distractors []string
	switch variant {
	case 0:
		done := b.Say(3, fmt.Sprintf("Decided the %s question: we're going with %s's idea.", event, who[1]), "Great, that settles it.")
		gold, evidence, distractors = c[1], []string{ev2, done}, []string{c[0]}
	case 1:
		done := b.Say(3, fmt.Sprintf("We didn't take %s's city for the %s in the end, %s's won the vote.", who[1], event, who[0]), "Good to have it decided.")
		gold, evidence, distractors = c[0], []string{ev1, done}, []string{c[1]}
	default:
		ev3 := b.Say(2, fmt.Sprintf("%s changed their mind about the %s and now prefers %s.", who[1], event, c[2]), "Fair enough.")
		done := b.Say(4, fmt.Sprintf("Settled the %s: we're doing whatever %s wanted.", event, who[1]), "Perfect, it's decided.")
		gold, evidence, distractors = c[2], []string{ev3, done}, []string{c[0], c[1]}
	}
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("picked-%d", i),
			QuestionType:      "multi-session-reasoning",
			Question:          fmt.Sprintf("Which city did we choose for the %s %s and %s were planning?", event, who[0], who[1]),
			ExpectedAnswer:    gold,
			DistractorAnswers: distractors,
		},
		EvidencePairIDs: evidence,
	}
}

// Elimination lists three drinks for a party and later rules two out, in
// separate messages, so the answer is the one never ruled out. Variants rule
// them out in either order and close with or without "the one left".
func Elimination(b *Builder, i int) challenge.Case {
	who := b.Pick(firstNames, 1)[0]
	d := b.Pick(drinksPool, 3)
	event := b.Any(events)
	ev := b.Say(0, fmt.Sprintf("Shortlist for the welcome drink at %s's %s: %s, %s or %s.", who, event, d[0], d[1], d[2]), "Good options, let me know which one wins.")
	out1, out2 := d[0], d[2]
	if i%2 == 1 {
		out1, out2 = d[2], d[0]
	}
	cut1 := b.Say(2, fmt.Sprintf("The caterer can't do %s for %s's %s, so that one's out.", out1, who, event), "Okay, crossing it off.")
	b.Filler()
	closing := "%s doesn't want %s at the %s either, so we'll go with the remaining one."
	if i%4 >= 2 {
		closing = "%s ruled out %s for the %s too. Done deciding."
	}
	cut2 := b.Say(4, fmt.Sprintf(closing, who, out2, event), "Sounds like the drink is settled.")
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                fmt.Sprintf("elimination-%d", i),
			QuestionType:      "multi-session-reasoning",
			Question:          fmt.Sprintf("What welcome drink did we settle on for %s's %s?", who, event),
			ExpectedAnswer:    d[1],
			DistractorAnswers: []string{out1, out2},
		},
		EvidencePairIDs: []string{ev, cut1, cut2},
	}
}

// Default is the family rotation.
var Default = []Family{RevertToOriginal, SwappedPair, PickedSuggestion, Elimination}
