// grade_replies grades harness replies to v14 program questions with the bench's own grader (grade.Memory).
//
// Input on stdin, one JSON object per line: {"seed": N, "id": "<case id>", "answer": "...", "final_text": "..."}.
// The case is regenerated from the seed (business and personal programs) and found by its id; the last path
// segment of a "kind/id" key is used. Output, one JSON object per line: {"id", "found", "score", "notes"}.
//
//	cd practice/gates/grader_probe/grade_replies && GOWORK=off GOPROXY=off GOFLAGS=-mod=mod go build -o grade_replies .
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/ditto-assistant/dittobench-datagen/grade"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
	"github.com/ditto-assistant/dittobench-datagen/universe"
)

type request struct {
	Seed      int64  `json:"seed"`
	ID        string `json:"id"`
	Answer    string `json:"answer"`
	FinalText string `json:"final_text"`
}

type result struct {
	ID    string   `json:"id"`
	Found bool     `json:"found"`
	Score float64  `json:"score"`
	Notes []string `json:"notes"`
}

func cases(seed int64) map[string]protocol.MemoryCase {
	biz, err := universe.GenerateV13ProgramsForVersion(seed, 16, protocol.BenchVersionV14)
	if err != nil {
		panic(err)
	}
	per, err := universe.GenerateV13PersonalProgramsForVersion(seed, 24, protocol.BenchVersionV14)
	if err != nil {
		panic(err)
	}
	out := map[string]protocol.MemoryCase{}
	for _, gc := range append(biz, per...) {
		mc := gc.Plan.Case
		mc.BenchVersion = protocol.BenchVersionV14
		out[last(mc.ID)] = mc
	}
	return out
}

func last(id string) string {
	return id[strings.LastIndex(id, "/")+1:]
}

func main() {
	bySeed := map[int64]map[string]protocol.MemoryCase{}
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 1<<20), 1<<24)
	out := json.NewEncoder(os.Stdout)
	for in.Scan() {
		var req request
		if err := json.Unmarshal(in.Bytes(), &req); err != nil {
			fmt.Fprintln(os.Stderr, "bad line:", err)
			continue
		}
		if bySeed[req.Seed] == nil {
			bySeed[req.Seed] = cases(req.Seed)
		}
		mc, ok := bySeed[req.Seed][last(req.ID)]
		res := result{ID: req.ID, Found: ok}
		if ok {
			v := grade.Memory(mc, protocol.RunResponse{Answer: req.Answer, FinalText: req.FinalText})
			res.Score, res.Notes = v.Score, v.Notes
		}
		_ = out.Encode(res)
	}
}
