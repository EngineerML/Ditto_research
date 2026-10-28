// Regrade the same memory answers under bench 14 and bench 13 with the official grader.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strconv"

	"github.com/ditto-assistant/dittobench-datagen/grade"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

type pair struct {
	Case      json.RawMessage `json:"case"`
	FinalText string          `json:"final_text"`
	Answer    string          `json:"answer"`
	RunScore  float64         `json:"run_score"`
	Match     float64         `json:"match"`
}

func main() {
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 16<<20), 16<<20)
	enc := json.NewEncoder(os.Stdout)
	for in.Scan() {
		var p pair
		if err := json.Unmarshal(in.Bytes(), &p); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		// the dataset writes bench_version as a string; the case struct wants an int
		var raw map[string]any
		_ = json.Unmarshal(p.Case, &raw)
		raw["bench_version"] = 14
		if s, ok := raw["bench_version"].(string); ok {
			n, _ := strconv.Atoi(s)
			raw["bench_version"] = n
		}
		b, _ := json.Marshal(raw)
		var mc protocol.MemoryCase
		if err := json.Unmarshal(b, &mc); err != nil {
			fmt.Fprintln(os.Stderr, "case:", err)
			os.Exit(1)
		}
		resp := protocol.RunResponse{FinalText: p.FinalText, Answer: p.Answer}
		mc.BenchVersion = 14
		v14 := grade.Memory(mc, resp)
		mc.BenchVersion = 13
		v13 := grade.Memory(mc, resp)
		_ = enc.Encode(map[string]any{
			"id": mc.ID, "type": mc.QuestionType, "run": p.RunScore, "match": p.Match,
			"v14": v14.Score, "v13": v13.Score, "v14_notes": v14.Notes, "v13_notes": v13.Notes,
		})
	}
}
