#!/bin/bash
# Run a lab module with the lab venv and the proxy settings: bash lab/run.sh lab.eval_offline --help
source /etc/profile.d/zz-proxy.sh 2>/dev/null
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python -m "$@"
