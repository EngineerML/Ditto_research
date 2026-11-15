#!/bin/bash
# Released beast-d41 v16-v19 and dan0l v59: layout, release metadata, and live column scores.
cd /home/bittensor/ditto/released || exit 1
for d in beast-d41-v16_* beast-d41-v17_* beast-d41-v18_* beast-d41-v19_* dan0l-v59_* crown-v228-v1_*; do
  echo "== $d"
  ls "$d" | head -20
  find "$d" -name '*.py' | wc -l
  ls -la --time-style=+%m-%dT%H:%M "$d" | head -3
done
