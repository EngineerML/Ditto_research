#!/bin/bash
# Build the served-text dumper (v15_atlas/servedgen, against the local datagen clone) and dump the served text of every
# corpus seed. The scorer serves the generator's text WITHOUT the dataset files' extra typo pass
# (services/dittobench-api/cmd/dittobench-api/main.go:1542-1571), so harness rules must be tested on these dumps.
#
#   bash v15_atlas/build_served.sh
set -e
cd /home/bittensor/ditto
mkdir -p /tmp/servedgen_build .cache/served
cp v15_atlas/servedgen/main.go /tmp/servedgen_build/
sed "s#=> .*#=> $PWD/repos/ditto-subnet/research/dittobench-datagen#" v15_atlas/servedgen/go.mod.in > /tmp/servedgen_build/go.mod
(cd /tmp/servedgen_build && GOFLAGS=-mod=mod GOCACHE=/tmp/servedgen_build/gocache go build -o "$OLDPWD/.cache/servedgen" .)
echo "built .cache/servedgen"
n=0
while read -r seed; do
  out=.cache/served/v15_s${seed}_served.json
  [ -f "$out" ] || .cache/servedgen -seed "$seed" -v 15 -out "$out"
  n=$((n + 1))
done < v15_atlas/corpus_seeds.txt
for seed in 5119792693744740612; do
  [ -f .cache/served/v15_s${seed}_served.json ] || .cache/servedgen -seed "$seed" -v 15 -out .cache/served/v15_s${seed}_served.json
done
echo "served dumps: $(ls .cache/served | wc -l)"
