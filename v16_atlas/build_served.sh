#!/bin/bash
# Build the bench-16 served-text dumper (v16_atlas/servedgen, against the local datagen clone) and dump every corpus
# seed to .cache/served16/v16_s<seed>.json: served case text, the seed's catalog and, for the selector bench only,
# expected tools and the connector plan.
#
#   bash v16_atlas/build_served.sh
set -e
cd /home/bittensor/ditto
B=/tmp/servedgen16_build
mkdir -p $B .cache/served16
cp v16_atlas/servedgen/main.go $B/
sed "s#=> .*#=> $PWD/repos/ditto-subnet/research/dittobench-datagen#; s#^module .*#module atlassurf16#" v16_atlas/servedgen/go.mod.in > $B/go.mod
(cd $B && GOFLAGS=-mod=mod GOCACHE=$B/gocache go build -o "$OLDPWD/.cache/servedgen16" .)
echo "built .cache/servedgen16 from datagen $(git -C repos/ditto-subnet rev-parse --short HEAD)"
while read -r seed; do
  out=.cache/served16/v16_s${seed}.json
  [ -f "$out" ] || .cache/servedgen16 -seed "$seed" -v 16 -out "$out"
done < v16_atlas/corpus_seeds.txt
echo "served dumps: $(ls .cache/served16 | wc -l)"
