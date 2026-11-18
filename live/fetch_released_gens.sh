#!/bin/bash
# Fetch the generator sources released since 2026-11-16 that are not downloaded yet (data only, nothing run).
cd /home/bittensor/ditto || exit 1
for pair in 33c60a4b:tetgol-v6 c955422c:querverweis-v3 a0b29a05:kinlist-v2 22caa69d:bounty-v1 b897a6bd:sn118-recall-v1 ce635a13:unnamed-ce635a13 00e58d65:unnamed-00e58d65 \
    b47a35f8:gan-v1-v2 ba5821d4:tern-gen-v1 d8a96d1d:unnamed-v8 0506250c:bounty-v2 ba2ee4d1:kinlist-v7 3ea2ae3e:v3h-worlds-v9; do
  p=${pair%%:*}; n=${pair#*:}
  if ls -d .cache/miner_gens/dl/${n}_* >/dev/null 2>&1; then echo "have $n"; continue; fi
  echo "== $n"
  bash live/fetch_by_prefix.sh "$p" "${n}_$p" 2>&1 | tail -12
done
