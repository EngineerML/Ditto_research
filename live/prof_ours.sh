#!/bin/bash
# Generator profiles for the current weak columns, all agents (ours vs leaders).
sed 's/\[:9\]/[:40]/' /home/bittensor/ditto/live/gen_profiles.py > /tmp/c228_prof_all.py
python3 /tmp/c228_prof_all.py > /tmp/c228_prof2.txt 2>&1
for g in f5659f80 663cf753 41a497e8 c955422c; do
  awk -v g="$g" '/^[0-9a-f]{8} /{on = ($1 == g)} on' /tmp/c228_prof2.txt | grep -E "^$g|overhorizoner|crown-v240|dan0l|Hades|beast-d41 v16|beast-d41 v2[34]|logan|crown-v24"
done
