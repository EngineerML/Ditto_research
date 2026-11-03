// Dumps the pre-surface-pass texts the dittobench-api run path serves to a
// harness (services/dittobench-api/cmd/dittobench-api/main.go:1542-1571),
// i.e. the generator output WITHOUT gen.V13ApplyArtifactSurfacePass.
package main

import (
	"encoding/json"
	"flag"
	"os"

	"github.com/ditto-assistant/dittobench-datagen/gen"
)

type pair struct {
	PairID    string `json:"pair_id"`
	SessionID string `json:"session_id"`
	Prompt    string `json:"prompt"`
	Response  string `json:"response"`
}
type tool struct {
	ID       string `json:"id"`
	Category string `json:"category"`
	Prompt   string `json:"prompt"`
	Pairs    []pair `json:"prerequisite_pairs"`
}
type mem struct {
	ID       string `json:"id"`
	Type     string `json:"question_type"`
	Question string `json:"question"`
}
type wave struct {
	Pairs []pair `json:"pairs"`
}
type out struct {
	Seed  int64  `json:"seed"`
	Tools []tool `json:"tool_cases"`
	Mem   []mem  `json:"memory_cases"`
	Waves []wave `json:"memory_waves"`
}

func main() {
	seed := flag.Int64("seed", 0, "")
	version := flag.Int("v", 15, "")
	path := flag.String("out", "", "")
	flag.Parse()
	prof, _ := gen.ProfileForVersion("full", *version)
	rng, err := gen.NewRNGForVersion(*seed, *version)
	if err != nil {
		panic(err)
	}
	toolCases, _ := gen.GenerateToolsForVersion(rng, *seed, prof.Tools, *version)
	suite, err := gen.GenerateMemorySuiteForVersion(rng, *seed, prof.Mem, prof.Waves, prof.RawPairsFrac, *version)
	if err != nil {
		panic(err)
	}
	iso, err := gen.GenerateIsolationForVersion(*seed, prof.Mem, prof.Waves, prof.IsoCases, *version)
	if err != nil {
		panic(err)
	}
	suite.Cases = append(suite.Cases, iso.Cases...)
	waves := gen.MergeMemoryWaves(suite.Waves, iso.SecondaryWave)
	o := out{Seed: *seed}
	for _, tc := range toolCases {
		t := tool{ID: tc.ID, Category: tc.Category, Prompt: tc.Prompt}
		for _, p := range tc.PrerequisitePairs {
			t.Pairs = append(t.Pairs, pair{p.PairID, p.SessionID, p.Prompt, p.Response})
		}
		o.Tools = append(o.Tools, t)
	}
	for _, c := range suite.Cases {
		o.Mem = append(o.Mem, mem{c.Case.ID, c.Case.QuestionType, c.Case.Question})
	}
	for _, w := range waves {
		var ww wave
		for _, p := range w.Pairs {
			ww.Pairs = append(ww.Pairs, pair{p.PairID, p.SessionID, p.Prompt, p.Response})
		}
		o.Waves = append(o.Waves, ww)
	}
	b, _ := json.Marshal(o)
	if err := os.WriteFile(*path, b, 0o644); err != nil {
		panic(err)
	}
}
