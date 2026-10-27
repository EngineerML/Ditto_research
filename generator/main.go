// Command generator is our entry in the DittoBench generator competition: a
// deterministic, CPU-only program that turns a GenerateRequest into a
// challenge pack. It is built on the public starter kit (builder, pools and
// this entry point; see LICENSE.starter-kit) with our own case families.
//
// The scorer builds this module offline and runs it in a no-network sandbox:
// it writes one request JSON object to stdin and reads one pack JSON object
// from stdout. Rehearse exactly that path locally:
//
//	cd ../repos/ditto-subnet/research/dittobench-datagen
//	go run ./cmd/challenge rehearse -dir "$OLDPWD" -hotkey <ss58> -seeds 3 -cases 80
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/ditto-assistant/dittobench-datagen/challenge"
	"horizon-generator/families"
)

// Name and Version identify this generator in the pack's provenance.
const (
	Name    = "horizon"
	Version = "1"
)

// MaxCases is the most cases the pools can fill without reusing a value. It
// matches challenge.MaxCases, the most cases_per_seed Platform can set: a
// generator that cannot fill the live cases_per_seed fails its round seed.
const MaxCases = 80

// Generate builds the pack for one request: the families in rotation, with a
// filler pair after every round, until the requested count is reached.
func Generate(req challenge.GenerateRequest) (challenge.Pack, error) {
	if err := req.Validate(); err != nil {
		return challenge.Pack{}, err
	}
	if req.Cases > MaxCases {
		return challenge.Pack{}, fmt.Errorf("generator fills at most %d cases, request asks for %d", MaxCases, req.Cases)
	}
	b := families.NewBuilder(req)
	for i := 0; b.Len() < req.Cases; i++ {
		round, family := i/len(families.Default), families.Default[i%len(families.Default)]
		b.Add(family(b, round))
		if i%len(families.Default) == len(families.Default)-1 {
			b.Filler()
		}
	}
	return b.Pack(req, Name, Version), nil
}

func main() {
	if err := run(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "generator:", err)
		os.Exit(1)
	}
}

func run(in io.Reader, out io.Writer) error {
	var req challenge.GenerateRequest
	if err := json.NewDecoder(in).Decode(&req); err != nil {
		return fmt.Errorf("read request: %w", err)
	}
	pack, err := Generate(req)
	if err != nil {
		return err
	}
	// Self-check before emitting: never ship a case the scorer will reject.
	raw, err := json.Marshal(pack)
	if err != nil {
		return err
	}
	if r := challenge.ValidateGenerated(raw, req); !r.Valid {
		b, _ := json.MarshalIndent(r.Issues, "", "  ")
		return fmt.Errorf("generated pack is invalid:\n%s", b)
	}
	_, err = out.Write(append(raw, '\n'))
	return err
}
