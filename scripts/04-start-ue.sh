#!/usr/bin/env bash
set -euo pipefail
source .env
docker rm -f "$UE_NAME" 2>/dev/null || true
GNB_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$GNB_NAME")
echo "GNB_IP=$GNB_IP"
docker run -d \
  --name "$UE_NAME" \
  --network "$NET_NAME" \
  --privileged \
  -v "$PWD/configs/oai/ue.conf:/opt/oai-nr-ue/etc/nr-ue.conf" \
  -e USE_ADDITIONAL_OPTIONS="--rfsim -r 106 --numerology 1 --band 78 -C 3619200000 -E --rfsimulator.serveraddr $GNB_IP" \
  oaisoftwarealliance/oai-nr-ue:develop

docker logs -f "$UE_NAME"
