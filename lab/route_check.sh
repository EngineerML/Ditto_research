#!/bin/bash
# Router accuracy of our harness (and Hades v6, dan0l v24) on the five competition seeds and the five
# second-check seeds, no chat calls (cached embeddings). Usage: bash lab/route_check.sh LABEL
cd "$(dirname "$0")/.." || exit 1
LABEL=${1:-now}
COMP=3590624429364033488,3135857511817419093,2680228380245708581,4126035199997736145,523400655585278561
OTHER=4242,11,12,13,14
mkdir -p practice/route_check
bash lab/run.sh lab.eval_router --seeds "$COMP" --out "practice/route_check/$LABEL.competition.json" 2>&1 | grep -vE "^\s*$" | tail -12
bash lab/run.sh lab.eval_router --seeds "$OTHER" --out "practice/route_check/$LABEL.other.json" 2>&1 | grep -vE "^\s*$" | tail -12
