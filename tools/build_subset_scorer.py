"""Build a copy of the official scorer that re-runs only chosen cases of a practice run.

    python3 tools/build_subset_scorer.py [REV]       # writes .cache/dittobench-api-subset

The copy is the upstream dittobench-api source at REV (default: the commit the practice
scorer .cache/dittobench-api was built from) with one change, active only when
DITTOBENCH_ONLY_CASES names a file of canonical case ids: after the dataset is generated,
hashed and projected, and after the tool prerequisite world is seeded, only the listed cases
(plus any earlier tool case a listed one runs after) are sent to the harness. Every memory
wave is still seeded at its place, so a memory case meets the same store it met in the full
run, and grading is untouched. Upstream clones under repos/ are not modified.

Also builds .cache/ditto-rescore, which re-aggregates a report's per-case scores with the
official scorer (composite, means, gate factors) once re-run cases are merged in.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
UPSTREAM = HERE / "repos" / "ditto-subnet"
WORK = HERE / ".cache" / "subset-scorer"
OUT = HERE / ".cache" / "dittobench-api-subset"
RESCORE = HERE / ".cache" / "ditto-rescore"

ONLY_CASES_GO = '''package main

// Local research patch (tools/build_subset_scorer.py), not upstream code.

import (
	"log"
	"os"
	"strings"

	"github.com/ditto-assistant/dittobench-datagen/gen"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

// onlyCases keeps the cases named in DITTOBENCH_ONLY_CASES (canonical ids, whitespace
// separated) and returns the lists unchanged when the variable is unset. A kept tool case
// that runs after an earlier case's mutation keeps that case too.
func onlyCases(p *gen.HarnessProjection, tools []protocol.ToolCase, mem []gen.StagedCase) ([]protocol.ToolCase, []gen.StagedCase) {
	path := strings.TrimSpace(os.Getenv("DITTOBENCH_ONLY_CASES"))
	if path == "" {
		return tools, mem
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("only-cases: %v", err)
	}
	keep := map[string]bool{}
	for _, id := range strings.Fields(string(raw)) {
		keep[id] = true
	}
	canonical := func(wire string) string {
		if p != nil {
			if id, err := p.InternalCaseID(wire); err == nil {
				return id
			}
		}
		return wire
	}
	byWire := make(map[string]protocol.ToolCase, len(tools))
	for _, c := range tools {
		byWire[c.ID] = c
	}
	for _, c := range tools {
		for d := c; keep[canonical(d.ID)] && d.RunAfterCaseID != ""; {
			dep, ok := byWire[d.RunAfterCaseID]
			if !ok || keep[canonical(dep.ID)] {
				break
			}
			keep[canonical(dep.ID)] = true
			log.Printf("only-cases: %s runs after %s, keeping both", canonical(d.ID), canonical(dep.ID))
			d = dep
		}
	}
	var keptTools []protocol.ToolCase
	for _, c := range tools {
		if keep[canonical(c.ID)] {
			keptTools = append(keptTools, c)
		}
	}
	var keptMem []gen.StagedCase
	for _, c := range mem {
		if keep[canonical(c.Case.ID)] {
			keptMem = append(keptMem, c)
		}
	}
	if found := len(keptTools) + len(keptMem); found == 0 || found < len(strings.Fields(string(raw))) {
		log.Fatalf("only-cases: %d ids listed, %d found in this dataset", len(strings.Fields(string(raw))), found)
	}
	log.Printf("only-cases: running %d tool and %d memory cases", len(keptTools), len(keptMem))
	return keptTools, keptMem
}
'''

RESCORE_GO = '''package main

// Local research tool (tools/build_subset_scorer.py), not upstream code: re-aggregate a
// practice report's per-case scores with the official scorer, after re-run cases were
// merged in. Prints the aggregate report and the gate factors as JSON.

import (
	"encoding/json"
	"log"
	"os"

	"github.com/ditto-assistant/dittobench-api/internal/scorer"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

func main() {
	if len(os.Args) != 2 {
		log.Fatal("usage: ditto-rescore REPORT.json")
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		log.Fatal(err)
	}
	var run struct {
		RunID        string `json:"run_id"`
		BenchVersion int    `json:"bench_version"`
		Report       struct {
			PerCase []protocol.CaseScore `json:"per_case"`
		} `json:"report"`
	}
	if err := json.Unmarshal(raw, &run); err != nil {
		log.Fatal(err)
	}
	perCase := scorer.ScoredPopulation(run.Report.PerCase)
	report := scorer.AggregateForVersion(run.RunID, perCase, run.BenchVersion)
	gates := map[string]any{
		"tool_efficiency":         scorer.ToolEfficiencyFactorForVersion(perCase, run.BenchVersion),
		"metamorphic_consistency": scorer.MetamorphicConsistency(perCase),
		"conversational_sanity":   report.ConversationalSanity,
	}
	if factor, ok := scorer.MemoryOverCallFactorForVersion(perCase, run.BenchVersion); ok {
		gates["memory_over_call"] = factor
	}
	report.PerCase = nil
	if err := json.NewEncoder(os.Stdout).Encode(map[string]any{"report": report, "gates": gates}); err != nil {
		log.Fatal(err)
	}
}
'''

# (pattern, replacement) on cmd/dittobench-api/main.go, each must match once
MAIN_EDITS = [
    # filter after the prerequisite world is seeded, before tool dispatch
    (r"^(\ttoolRunUserID := \"\"\n)",
     "\tallToolCases := toolCases\n\ttoolCases, memSuite.Cases = onlyCases(harnessProjection, toolCases, memSuite.Cases)\n\\1"),
    # record tokens for claim provenance still come from every tool case
    (r"(recordTokens := v13RecordTokens\(req\.BenchVersion, append\(append\(\[\]protocol\.SeedRequest\(nil\), memSuite\.Waves\.\.\.\), iso\.SecondaryWave\), )toolCases\)",
     r"\1allToolCases)"),
]


def scorer_revision() -> str:
    """The upstream commit the practice scorer (.cache/dittobench-api) was built from."""
    info = subprocess.run(["go", "version", "-m", str(HERE / ".cache" / "dittobench-api")], capture_output=True, text=True, check=True).stdout
    return re.search(r"vcs\.revision=([0-9a-f]{40})", info).group(1)


def main() -> int:
    rev = sys.argv[1] if len(sys.argv) > 1 else scorer_revision()
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(UPSTREAM), "archive", rev, "services/dittobench-api", "research/dittobench-datagen"],
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(WORK)], input=archive, check=True)
    print(f"upstream source at {rev[:12]}")
    cmd = WORK / "services" / "dittobench-api" / "cmd" / "dittobench-api"
    text = (cmd / "main.go").read_text()
    for pattern, replacement in MAIN_EDITS:
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
        if count != 1:
            print(f"main.go: patch point not found: {pattern[:60]}", file=sys.stderr)
            return 1
    (cmd / "main.go").write_text(text)
    (cmd / "only_cases.go").write_text(ONLY_CASES_GO)
    (cmd.parent / "ditto-rescore").mkdir()
    (cmd.parent / "ditto-rescore" / "main.go").write_text(RESCORE_GO)
    api = WORK / "services" / "dittobench-api"
    subprocess.run(["go", "build", "-o", str(OUT), "./cmd/dittobench-api"], cwd=api, check=True)
    subprocess.run(["go", "build", "-o", str(RESCORE), "./cmd/ditto-rescore"], cwd=api, check=True)
    print(f"built {OUT} and {RESCORE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
