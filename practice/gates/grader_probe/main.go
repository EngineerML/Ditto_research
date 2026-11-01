package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/ditto-assistant/dittobench-datagen/grade"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
	"github.com/ditto-assistant/dittobench-datagen/universe"
)

type probe struct {
	name   string
	slot   string
	prose  string
}

func fill(s, e, d string) string {
	return strings.ReplaceAll(strings.ReplaceAll(s, "{E}", e), "{D}", d)
}

func timeVariants(e string) []string {
	parts := strings.Split(e, ":")
	if len(parts) != 2 || len(e) != 5 {
		return nil
	}
	h, _ := strconv.Atoi(parts[0])
	m, _ := strconv.Atoi(parts[1])
	h12 := h % 12
	if h12 == 0 {
		h12 = 12
	}
	suf := "a.m."
	if h >= 12 {
		suf = "p.m."
	}
	return []string{
		fmt.Sprintf("%d:%02d %s", h12, m, suf),
		fmt.Sprintf("%d:%02d", h12, m),
		fmt.Sprintf("%d%s", h12, map[bool]string{true: "pm", false: "am"}[h >= 12]),
	}
}

func main() {
	seed := int64(897500335867350922)
	if len(os.Args) > 1 {
		seed, _ = strconv.ParseInt(os.Args[1], 10, 64)
	}
	biz, err := universe.GenerateV13ProgramsForVersion(seed, 16, protocol.BenchVersionV14)
	if err != nil {
		panic(err)
	}
	per, err := universe.GenerateV13PersonalProgramsForVersion(seed, 24, protocol.BenchVersionV14)
	if err != nil {
		panic(err)
	}
	all := append(biz, per...)
	templates := []probe{
		{"bare", "", "{E}"},
		{"sentence", "", "The answer is {E}."},
		{"now", "", "It is {E} now."},
		{"md-bold", "", "**{E}**"},
		{"orig-clause", "", "It is {E}, back to the original entry."},
		{"orig-same-clause", "", "It is back to the original entry {E}."},
		{"prev-paren", "", "{E} (back to the previous entry)."},
		{"before-then", "", "{E} before then."},
		{"initially-paren", "", "{E} (as initially recorded)."},
		{"no-other-change", "", "{E}. No other change applies."},
		{"actually-after", "", "{E}. Actually, that is the current one."},
		{"there-is-no", "", "{E}; there is no later change."},
		{"was-never", "", "{E}, because the change was never adopted."},
		{"not-stated", "", "{E} (later value not stated)."},
		{"reject-decoy", "", "{E}, not {D}."},
		{"mention-decoy", "", "{E}. The unrelated workstream has {D}."},
		{"decoy-sep-sentence-weak", "", "It is {E}. {D} was the other one."},
		{"hedge", "", "Either {E} or {D}."},
		{"question", "", "Is it {E}?"},
		{"slot-only", "{E}", ""},
		{"slot+prose", "{E}", "The answer is {E}."},
		{"slot+prose-decoy-other-sentence", "{E}", "The answer is {E}. The unrelated one is {D}."},
		{"slot+prose-missing", "{E}", "See the notes."},
		{"slot-wrong-prose-right", "nothing", "The answer is {E}."},
	}
	for _, gc := range all {
		mc := gc.Plan.Case
		if gc.Provenance.Relation != "base" {
			continue
		}
		mc.BenchVersion = protocol.BenchVersionV14
		d := ""
		if len(mc.DistractorAnswers) > 0 {
			d = mc.DistractorAnswers[0]
		}
		e := mc.ExpectedAnswer
		fmt.Printf("=== %s | op=%s | E=%q | D=%v\n", mc.QuestionType, gc.Provenance.Program.Op, e, mc.DistractorAnswers)
		fmt.Printf("    claims:")
		for _, c := range mc.Claims {
			fmt.Printf(" [%s %q w=%.2f crit=%v]", c.Kind, c.Expected, c.Weight, c.Critical)
		}
		fmt.Println()
		ps := append([]probe(nil), templates...)
		if os.Getenv("SKIPCHAIN") != "" && gc.Provenance.Program.Op == "fold_supersession" && !strings.Contains(e, ":") && !strings.Contains(e, "-") {
			continue
		}
		ps = append(ps, extra(mc, e, d)...)
		for _, tv := range timeVariants(e) {
			ps = append(ps, probe{"time:" + tv, "", tv})
		}
		if mc.AnswerKind == protocol.AnswerList && len(mc.AnswerItems) > 0 {
			ps = append(ps,
				probe{"list-comma", "", strings.Join(mc.AnswerItems, ", ")},
				probe{"list-and", "", strings.Join(mc.AnswerItems[:len(mc.AnswerItems)-1], ", ") + " and " + mc.AnswerItems[len(mc.AnswerItems)-1]},
				probe{"list-bullets", "", "- " + strings.Join(mc.AnswerItems, "\n- ")},
				probe{"list-missing-one", "", strings.Join(mc.AnswerItems[1:], ", ")},
				probe{"list+removed-was-removed", "", strings.Join(mc.AnswerItems, ", ") + ". The " + d + " was removed."},
				probe{"list+removed-swapped", "", strings.Join(mc.AnswerItems, ", ") + " (the " + d + " was swapped out)."},
				probe{"list+no-removed", "", strings.Join(mc.AnswerItems, ", ") + "; no " + d + "."},
			)
		}
		for _, p := range ps {
			resp := protocol.RunResponse{Answer: fill(p.slot, e, d), FinalText: fill(p.prose, e, d)}
			v := grade.Memory(mc, resp)
			note := strings.Join(v.Notes, " | ")
			if len(note) > 150 {
				note = note[:150]
			}
			if os.Getenv("COMPACT") != "" {
				fmt.Printf(" %s=%.2f", p.name, v.Score)
				continue
			}
			fmt.Printf("    %-34s %.3f  %s\n", p.name, v.Score, note)
		}
		fmt.Println()
	}
}

func extra(mc protocol.MemoryCase, e, d string) []probe {
	var out []probe
	if len(e) == 10 && e[4] == '-' && e[7] == '-' {
		y, _ := strconv.Atoi(e[:4])
		m, _ := strconv.Atoi(e[5:7])
		dd, _ := strconv.Atoi(e[8:])
		months := []string{"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}
		mn := months[m-1]
		out = append(out,
			probe{"date:iso-comma", "", fmt.Sprintf("It is %s, as rescheduled.", e)},
			probe{"date:name", "", fmt.Sprintf("%s %d, %d", mn, dd, y)},
			probe{"date:name-comma", "", fmt.Sprintf("It is on %s %d, %d, as rescheduled.", mn, dd, y)},
			probe{"date:noyear", "", fmt.Sprintf("%d %s", dd, mn)},
			probe{"date:with-old-date", "", fmt.Sprintf("%s %d, %d (moved from 16 May 2026).", mn, dd, y)},
			probe{"date:old-rejected", "", fmt.Sprintf("%s %d, %d, not 16 May 2026.", mn, dd, y)},
			probe{"date:old-previously", "", fmt.Sprintf("%s %d, %d; previously 16 May 2026.", mn, dd, y)},
			probe{"date:weekday", "", fmt.Sprintf("Friday, %s %d, %d", mn, dd, y)},
		)
	}
	if mc.AnswerKind == protocol.AnswerList && len(mc.AnswerItems) == 2 {
		a, b := mc.AnswerItems[0], mc.AnswerItems[1]
		f := func(s string) string { return strings.ReplaceAll(strings.ReplaceAll(strings.ReplaceAll(s, "{A}", a), "{B}", b), "{D}", d) }
		for _, t := range []struct{ n, s string }{
			{"pair:owned-by", "{A}, owned by {B}."},
			{"pair:dash", "{A} — {B}"},
			{"pair:paren", "{A} ({B})"},
			{"pair:labels", "Next open step: {A}. Owner: {B}."},
			{"pair:owns", "{B} owns {A}."},
			{"pair:to-verb", "To {A}; {B} is responsible."},
			{"pair:other-step-done", "{A}, owned by {B}. The {D} step is closed."},
			{"pair:other-step-past", "{A}, owned by {B}. Someone already did the earlier one."},
			{"pair:only-step", "{A}"},
			{"pair:only-owner", "{B}"},
			{"pair:wrong-owner", "{A}, owned by Zed Quux."},
		} {
			out = append(out, probe{t.n, "", f(t.s)})
		}
	}
	return out
}
