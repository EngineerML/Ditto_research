// Grade a harness's answers to a challenge pack's cases with the official memory grader.
//
//	go run ./tools/gradepack < rows.jsonl
//
// Each input line is {"case": <pack case>, "answer": "...", "final_text": "...", "bench": N}; each output line is
// {"id", "bench", "score", "notes"}. A local panel of fewer than three agents is not graded by the challenge
// scorer, so this grades a single agent's traced answers the way a scored column grades them.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"

	"github.com/ditto-assistant/dittobench-datagen/grade"
	"github.com/ditto-assistant/dittobench-datagen/protocol"
)

type row struct {
	Case      protocol.MemoryCase `json:"case"`
	Answer    string              `json:"answer"`
	FinalText string              `json:"final_text"`
	Bench     int                 `json:"bench"`
}

func main() {
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 64<<20), 64<<20)
	enc := json.NewEncoder(os.Stdout)
	for in.Scan() {
		var r row
		if err := json.Unmarshal(in.Bytes(), &r); err != nil {
			fmt.Fprintln(os.Stderr, "row:", err)
			os.Exit(1)
		}
		r.Case.BenchVersion = r.Bench
		v := grade.Memory(r.Case, protocol.RunResponse{Answer: r.Answer, FinalText: r.FinalText})
		_ = enc.Encode(map[string]any{"id": r.Case.ID, "bench": r.Bench, "score": v.Score, "notes": v.Notes})
	}
}
