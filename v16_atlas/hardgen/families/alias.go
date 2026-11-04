package families

// Alias families: list questions whose items are stated under different names for one person.
//
// Built to reproduce the shape the live v16 miner column c0 appears to use (all top agents score it at about 0.5 a
// case, which is the official "two-item nickname list" of challenge/half_credit_test.go): one item is stated under the
// person's full name, the other under a nickname that only an identity record links to them. A look-alike person with
// a nickname one letter off has an item of their own, which is the distractor; naming it scores 0.

import (
	"fmt"
	"strings"

	"github.com/ditto-assistant/dittobench-datagen/challenge"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

type category struct {
	one, many string
	verb      []string // "{who} loves {item}" style sentences; %[1]s person, %[2]s item, %[3]s category word
	asks      []string // questions; %[1]s person, %[2]s plural category, %[3]s count word
	heads     []string
	tails     []string
}

var categories = []category{
	{one: "bakery", many: "bakeries",
		verb:  []string{"%[1]s keeps telling me %[2]s is the best %[3]s in town.", "%[1]s took me to %[2]s on Saturday, apparently it's their favourite %[3]s.", "Turns out %[1]s is a regular at %[2]s, they love that %[3]s."},
		asks:  []string{"Which %[3]s %[2]s does %[1]s love?", "Name the %[3]s %[2]s %[1]s is always raving about.", "What are the %[3]s %[2]s %[1]s likes best?"},
		heads: []string{"Crumb", "Thistle", "Hearth", "Golden", "Rye", "Larch", "Copper", "Saffron", "Bramble", "Wheaten", "Linden", "Ember", "Maple", "Sorrel", "Juniper", "Fennel"},
		tails: []string{"Loaves", "Oven", "Bakehouse", "Crust", "Kitchen", "Rise", "Hearth", "Mill"}},
	{one: "podcast", many: "podcasts",
		verb:  []string{"%[1]s won't stop recommending %[2]s, says it's the best %[3]s going.", "%[1]s has been bingeing %[2]s all week, their favourite %[3]s by far.", "Apparently %[1]s never misses an episode of %[2]s."},
		asks:  []string{"Which %[3]s %[2]s does %[1]s listen to?", "Name the %[3]s %[2]s %[1]s keeps recommending.", "What are the %[3]s %[2]s %[1]s is into?"},
		heads: []string{"Quiet", "Signal", "Second", "Paper", "Night", "Open", "Slow", "Field", "Static", "Hidden", "Long", "Bright", "Small", "Deep", "Cold", "Lucky"},
		tails: []string{"Hours", "Notes", "Wire", "Archive", "Frequency", "Hour", "Dispatch", "Margins"}},
	{one: "hiking trail", many: "hiking trails",
		verb:  []string{"%[1]s says %[2]s is the best %[3]s around here.", "%[1]s did %[2]s again last weekend, their go-to %[3]s.", "%[1]s swears by %[2]s whenever they need a %[3]s."},
		asks:  []string{"Which %[3]s %[2]s does %[1]s love?", "Name the %[3]s %[2]s %[1]s keeps going back to.", "What are the %[3]s %[2]s %[1]s likes most?"},
		heads: []string{"Heron", "Falcon", "Cedar", "Granite", "Willow", "Osprey", "Bracken", "Alder", "Kestrel", "Flint", "Aspen", "Rowan", "Marten", "Plover", "Sedge", "Tamarack"},
		tails: []string{"Ridge", "Loop", "Pass", "Hollow", "Crossing", "Spur", "Gap", "Traverse"}},
	{one: "board game", many: "board games",
		verb:  []string{"%[1]s brought %[2]s to game night again, their favourite %[3]s.", "%[1]s keeps asking to play %[2]s, the %[3]s they love most.", "%[1]s bought a second copy of %[2]s, they're obsessed with that %[3]s."},
		asks:  []string{"Which %[3]s %[2]s does %[1]s love?", "Name the %[3]s %[2]s %[1]s always wants to play.", "What are the %[3]s %[2]s %[1]s is obsessed with?"},
		heads: []string{"Harbor", "Tower", "Lantern", "Orchard", "Clockwork", "Meadow", "Canal", "Citadel", "Glacier", "Bazaar", "Vineyard", "Lighthouse", "Quarry", "Atlas", "Beacon", "Harvest"},
		tails: []string{"Lords", "Kings", "Traders", "Builders", "Heist", "Rush", "League", "Saga"}},
	{one: "restaurant", many: "restaurants",
		verb:  []string{"%[1]s booked %[2]s for their birthday, it's their favourite %[3]s.", "%[1]s eats at %[2]s every Friday, they love that %[3]s.", "%[1]s says nobody beats %[2]s as a %[3]s."},
		asks:  []string{"Which %[3]s %[2]s does %[1]s love?", "Name the %[3]s %[2]s %[1]s always picks.", "What are the %[3]s %[2]s %[1]s likes best?"},
		heads: []string{"Olive", "Salt", "Basil", "Pepper", "Clove", "Indigo", "Lotus", "Tamarind", "Fig", "Quince", "Anise", "Citrus", "Sumac", "Paprika", "Mango", "Ginger"},
		tails: []string{"Table", "Room", "Grill", "House", "Kitchen", "Garden", "Bistro", "Cellar"}},
}

var personFirst = []string{"Imogen", "Harriet", "Desmond", "Rosalind", "Barnaby", "Philippa", "Cornelius", "Josephine", "Leopold", "Wilhelmina",
	"Theodora", "Augustus", "Florence", "Benedict", "Penelope", "Montgomery", "Genevieve", "Archibald", "Clementine", "Bartholomew",
	"Marguerite", "Reginald", "Henrietta", "Percival", "Evangeline", "Fitzgerald", "Arabella", "Sebastian", "Ottoline", "Lysander"}
var personLast = []string{"Vale", "Hartley", "Pemberton", "Ashcombe", "Thorne", "Kingsley", "Mallory", "Whitlock", "Davenport", "Fairbairn",
	"Holloway", "Lockwood", "Merriweather", "Ravensworth", "Sutherland", "Underhill", "Wetherby", "Brightwell", "Carrington", "Ellsworth"}
var nicknames = []string{"Midge", "Bex", "Teddy", "Pip", "Bunny", "Ziggy", "Dot", "Kit", "Moss", "Rory", "Tash", "Wren", "Biscuit", "Peaches",
	"Sunny", "Bean", "Scout", "Lark", "Dusty", "Jinx", "Pickle", "Bramble", "Cricket", "Noodle", "Fudge", "Maple", "Rusty", "Sparky",
	"Tilly", "Boots", "Chip", "Goose", "Buzz", "Mac", "Nell", "Otto", "Puck", "Remy", "Sage", "Tuck", "Vinnie", "Zola",
	"Ace", "Birdie", "Coco", "Dodger", "Echo", "Finch", "Gigi", "Hopper", "Iggy", "Jojo", "Kiki", "Loki", "Mims", "Nibs", "Ozzy", "Poppy",
	"Quill", "Roo", "Skip", "Taffy", "Ush", "Vix", "Waffles", "Yaya", "Zippy", "Bubba", "Cosmo", "Dimples", "Elvis", "Fizz", "Gus", "Hutch",
	"Ivy", "Jazz", "Kip", "Lulu", "Mojo", "Nuts", "Oddie", "Pogo", "Rocket", "Smudge", "Tiger", "Ziggs", "Banjo", "Clover", "Dash", "Ellie"}

var identityLines = []string{
	"Quick note so I don't mix people up: %[1]s goes by \"%[2]s\" with friends.",
	"Everyone at book club calls %[1]s \"%[2]s\", by the way.",
	"For the record, %[1]s is \"%[2]s\" to pretty much everyone.",
}
var identityReplies = []string{"Got it, I'll remember that.", "Noted.", "Thanks, that helps."}
var countWords = map[int]string{2: "two", 3: "three"}

// lookAlike changes one vowel of a nickname, so two people's nicknames differ by a letter.
func lookAlike(nick string) string {
	swap := map[rune]rune{'a': 'e', 'e': 'i', 'i': 'o', 'o': 'u', 'u': 'a'}
	r := []rune(nick)
	for k := len(r) - 1; k > 0; k-- {
		if to, ok := swap[r[k]]; ok {
			r[k] = to
			return string(r)
		}
	}
	return nick + "y"
}

// person reserves a full name and a nickname, and returns the full name, nickname and initials form ("I. Vale").
func (b *Builder) person() (string, string, string) {
	for try := 0; try < 10000; try++ {
		first := personFirst[b.Rng.Intn(len(personFirst))]
		last := personLast[b.Rng.Intn(len(personLast))]
		full, initials := first+" "+last, fmt.Sprintf("%s. %s", first[:1], last)
		if b.used[full] || b.used[initials] {
			continue
		}
		b.used[full], b.used[initials] = true, true
		nick := b.Pick(nicknames, 1)[0]
		b.used[lookAlike(nick)] = true
		return full, nick, initials
	}
	panic("person pool exhausted")
}

// items reserves n distinct two-word names in the category.
func (b *Builder) items(c category, n int) []string {
	var out []string
	for len(out) < n {
		v := c.heads[b.Rng.Intn(len(c.heads))] + " " + c.tails[b.Rng.Intn(len(c.tails))]
		if !b.used[v] {
			b.used[v] = true
			out = append(out, v)
		}
	}
	return out
}

func (b *Builder) line(c category, who, item string) string {
	return fmt.Sprintf(c.verb[b.Rng.Intn(len(c.verb))], who, item, c.one)
}

func (b *Builder) wave() int { return b.Rng.Intn(Waves) }

func listCase(id, qtype, question string, gold, wrong, evidence []string) challenge.Case {
	return challenge.Case{
		MemoryCase: protocol.MemoryCase{
			ID:                id,
			QuestionType:      qtype,
			Question:          question,
			ExpectedAnswer:    strings.Join(gold, " and "),
			AnswerKind:        protocol.AnswerList,
			AnswerItems:       gold,
			DistractorAnswers: wrong,
		},
		EvidencePairIDs: evidence,
	}
}

// lookAlikePerson seeds a second person whose nickname is one letter off, with an item of their own.
func (b *Builder) lookAlikePerson(c category, nick string) string {
	full, _, _ := b.person()
	other := lookAlike(nick)
	item := b.items(c, 1)[0]
	b.Say(b.wave(), fmt.Sprintf(identityLines[b.Rng.Intn(len(identityLines))], full, other), identityReplies[b.Rng.Intn(len(identityReplies))])
	b.Say(b.wave(), b.line(c, other, item), "Sounds like a good one.")
	return item
}

var dislikeLines = []string{
	"%[1]s tried %[2]s once and hated it, never again apparently.",
	"%[1]s says %[2]s was a total letdown and won't go back.",
	"Don't suggest %[2]s to %[1]s, they really can't stand it.",
}

// disliked seeds an item the person turned down, under one of their names: a second wrong item in memory.
func (b *Builder) disliked(c category, who string) string {
	item := b.items(c, 1)[0]
	b.Say(b.wave(), fmt.Sprintf(dislikeLines[b.Rng.Intn(len(dislikeLines))], who, item), "Noted, I'll steer clear of that one.")
	return item
}

// NicknameList asks by full name; one item is stated under the full name, one under the nickname.
func NicknameList(b *Builder, i int) challenge.Case {
	c := categories[(i+b.Rng.Intn(len(categories)))%len(categories)]
	full, nick, _ := b.person()
	it := b.items(c, 2)
	id := b.Say(b.wave(), fmt.Sprintf(identityLines[b.Rng.Intn(len(identityLines))], full, nick), identityReplies[b.Rng.Intn(len(identityReplies))])
	e1 := b.Say(b.wave(), b.line(c, full, it[0]), "Good to know.")
	e2 := b.Say(b.wave(), b.line(c, nick, it[1]), "I'll keep that in mind.")
	wrong := []string{b.lookAlikePerson(c, nick), b.disliked(c, nick)}
	q := fmt.Sprintf(c.asks[b.Rng.Intn(len(c.asks))], full, c.many, countWords[2])
	return listCase(fmt.Sprintf("nickname-list-%d", i), "two-item-nickname-list", q, it, wrong, []string{id, e1, e2})
}

// NicknameListReverse asks by nickname; one item is stated under the nickname, one under the full name.
func NicknameListReverse(b *Builder, i int) challenge.Case {
	c := categories[(i+1+b.Rng.Intn(len(categories)))%len(categories)]
	full, nick, _ := b.person()
	it := b.items(c, 2)
	id := b.Say(b.wave(), fmt.Sprintf(identityLines[b.Rng.Intn(len(identityLines))], full, nick), identityReplies[b.Rng.Intn(len(identityReplies))])
	e1 := b.Say(b.wave(), b.line(c, nick, it[0]), "Good to know.")
	e2 := b.Say(b.wave(), b.line(c, full, it[1]), "I'll keep that in mind.")
	wrong := []string{b.lookAlikePerson(c, nick), b.disliked(c, full), b.disliked(c, nick)}
	q := fmt.Sprintf(c.asks[b.Rng.Intn(len(c.asks))], nick, c.many, countWords[2])
	return listCase(fmt.Sprintf("nickname-list-reverse-%d", i), "two-item-nickname-list", q, it, wrong, []string{id, e1, e2})
}

// AliasListThree states three items under the full name, the nickname and the initials form.
func AliasListThree(b *Builder, i int) challenge.Case {
	c := categories[(i+2+b.Rng.Intn(len(categories)))%len(categories)]
	full, nick, initials := b.person()
	it := b.items(c, 3)
	id := b.Say(b.wave(), fmt.Sprintf(identityLines[b.Rng.Intn(len(identityLines))], full, nick), identityReplies[b.Rng.Intn(len(identityReplies))])
	idi := b.Say(b.wave(), fmt.Sprintf("On the club roster %s is listed as %s.", full, initials), "Okay, noted.")
	e1 := b.Say(b.wave(), b.line(c, full, it[0]), "Good to know.")
	e2 := b.Say(b.wave(), b.line(c, nick, it[1]), "I'll keep that in mind.")
	e3 := b.Say(b.wave(), b.line(c, initials, it[2]), "Nice.")
	wrong := []string{b.lookAlikePerson(c, nick), b.disliked(c, nick)}
	q := fmt.Sprintf(c.asks[b.Rng.Intn(len(c.asks))], full, c.many, countWords[3])
	return listCase(fmt.Sprintf("alias-list-three-%d", i), "three-item-alias-list", q, it, wrong, []string{id, idi, e1, e2, e3})
}

// NicknameListUpdate states one item under the full name and one under the nickname, then drops the nickname item
// for a new one in a later wave.
func NicknameListUpdate(b *Builder, i int) challenge.Case {
	c := categories[(i+3+b.Rng.Intn(len(categories)))%len(categories)]
	full, nick, _ := b.person()
	it := b.items(c, 3)
	id := b.Say(0, fmt.Sprintf(identityLines[b.Rng.Intn(len(identityLines))], full, nick), identityReplies[b.Rng.Intn(len(identityReplies))])
	e1 := b.Say(b.wave(), b.line(c, full, it[0]), "Good to know.")
	b.Say(0, b.line(c, nick, it[1]), "I'll keep that in mind.")
	e3 := b.Say(Waves-1, fmt.Sprintf("%s says %s has gone downhill, so these days it's %s instead.", nick, it[1], it[2]), "Fair enough, tastes change.")
	wrong := b.lookAlikePerson(c, nick)
	q := fmt.Sprintf(c.asks[b.Rng.Intn(len(c.asks))], full, c.many, countWords[2])
	return listCase(fmt.Sprintf("nickname-list-update-%d", i), "two-item-nickname-list-update", q, []string{it[0], it[2]}, []string{it[1], wrong}, []string{id, e1, e3})
}
