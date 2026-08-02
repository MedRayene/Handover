#!/usr/bin/env bash
set -euo pipefail
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Networks}}\t{{.Ports}}'
echo; echo '--- NGAP/SCTP in VPLMN ---'
docker exec vplmn-core bash -lc 'ss -lnp | grep 38412 || true'
echo; echo '--- Last core log lines ---'
tail -n 80 logs/hplmn.log logs/vplmn.log 2>/dev/null || true
