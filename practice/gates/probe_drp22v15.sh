#!/bin/bash
# The screener's zero-token probe battery (scripted model, no model calls) on images built from a tarball, at
# the given bench. Writes practice/probe_<NAME>_{prepare,battery}.json.
#
#   bash practice/gates/probe_drp22v15.sh [NAME=TARBALL ...]     (default: our drp22v15 and the released v22)
#
# The Docker client config on this machine sets the WSL proxy, which docker run copies into every container;
# inside the probe's closed network the gateway's health check then goes to the proxy and fails ("Network
# unreachable"). The probe runs with a client config that has no proxies (buildx kept), as a validator
# sandbox has no proxy.
source /etc/profile.d/zz-proxy.sh
D=/home/bittensor/ditto
PY=$D/.cache/screener-venv/bin/python
export DOCKER_CONFIG=/tmp/docker-noproxy
mkdir -p $DOCKER_CONFIG
echo '{}' > $DOCKER_CONFIG/config.json
for sub in buildx cli-plugins; do
  [ -e ~/.docker/$sub ] && [ ! -e $DOCKER_CONFIG/$sub ] && ln -s ~/.docker/$sub $DOCKER_CONFIG/$sub
done
[ $# -eq 0 ] && set -- drp22v15=$D/practice/submission_drp22v15.tgz drp22ref=$D/released/DrPresident-v22_eeb26552/agent.tar.gz
cd $D/repos/ditto-subnet/workers/screener || exit 1
for pair in "$@"; do
  NAME=${pair%%=*}; PKG=${pair#*=}
  SHA=$(sha256sum $PKG | cut -d' ' -f1)
  S=/tmp/probe_$NAME; rm -rf $S
  echo "===== $NAME ($(basename $PKG), ${SHA:0:12})"
  timeout 900 $PY -m ditto_screener.probe_review prepare --archive $PKG --sha256 $SHA --out $S --bench-version ${BENCH:-15} --allow-host-daemon --keep > $D/practice/probe_${NAME}_prepare.json 2>&1
  echo "prepare exit $?"; tail -c 300 $D/practice/probe_${NAME}_prepare.json; echo
  timeout 900 $PY -m ditto_screener.probe_review battery --session $S > $D/practice/probe_${NAME}_battery.json 2>&1
  echo "battery exit $?"
  $PY -m ditto_screener.probe_review stop --session $S > /dev/null 2>&1
done
