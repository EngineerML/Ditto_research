#!/bin/bash
cd "$(dirname "$0")"
export GOWORK=off GOPROXY=off GOFLAGS=-mod=mod SKIPCHAIN=1 COMPACT=1
go build -o probe.bin . || exit 1
for s in 3874019265530918471 1139645001622862899 5502918374460173285 3702146601065143693 138287359920490853 1682118813209272281 6120847739265810593 4554539008411854322 2330430686809638580; do
  echo "SEED $s"
  ./probe.bin $s | grep -A2 -E 'op=(first_open_step|read|as_of|join_|fold_holder|nth_by|before_by|after_by)|op=fold_supersession \| E="[0-9]{2}:'
done
