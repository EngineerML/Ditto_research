// Dumps what the bench-16 run path serves a harness for one seed: the datagen half's tool and memory cases in their
// pre-surface-pass text (services/dittobench-api/cmd/dittobench-api/main.go, generation block), the seed's catalog
// (catalog.CatalogForSeed) and, for the tool-list selector bench only, each tool case's expected tools and the
// seed's connector plan. A harness never sees the expected tools or the plan.
package main

import (
	"encoding/json"
	"flag"
	"os"

	"github.com/ditto-assistant/dittobench-datagen/catalog"
	"github.com/ditto-assistant/dittobench-datagen/gen"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

type tool struct {
	ID       string   `json:"id"`
	Category string   `json:"category"`
	Prompt   string   `json:"prompt"`
	Expected []string `json:"expected_tools"`
	Behavior string   `json:"expected_behavior,omitempty"`
}

type mem struct {
	ID       string `json:"id"`
	Type     string `json:"question_type"`
	Question string `json:"question"`
}

type out struct {
	Seed    int64                     `json:"seed"`
	Catalog []protocol.ToolDefinition `json:"catalog"`
	Plan    catalog.V16ConnectorPlan  `json:"connector_plan"`
	Tools   []tool                    `json:"tool_cases"`
	Mem     []mem                     `json:"memory_cases"`
}

func main() {
	seed := flag.Int64("seed", 0, "")
	version := flag.Int("v", 16, "")
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
	o := out{Seed: *seed, Catalog: catalog.CatalogForSeed(*version, *seed), Plan: catalog.V16ConnectorPlanForSeed(*seed)}
	for _, tc := range toolCases {
		t := tool{ID: tc.ID, Category: tc.Category, Prompt: tc.Prompt, Behavior: tc.ExpectedBehavior}
		for _, e := range tc.ExpectedTools {
			t.Expected = append(t.Expected, e.Name)
		}
		o.Tools = append(o.Tools, t)
	}
	for _, c := range suite.Cases {
		o.Mem = append(o.Mem, mem{c.Case.ID, c.Case.QuestionType, c.Case.Question})
	}
	b, _ := json.Marshal(o)
	if err := os.WriteFile(*path, b, 0o644); err != nil {
		panic(err)
	}
}
