#!/usr/bin/env bash
set -euo pipefail
source .env

for cfg in configs/oai/gnb.conf configs/oai/neighbour-config-rfsim.conf; do
  if [ ! -f "$PWD/$cfg" ]; then
    echo "ERROR: $cfg is missing or is a directory (Docker would silently create an empty dir)."
    echo "       Create the file first, then re-run this script."
    exit 1
  fi
done

docker rm -f "$GNB_NAME" 2>/dev/null || true
docker run -d \
  --name "$GNB_NAME" \
  --network "$NET_NAME" \
  --privileged \
  -v "$PWD/configs/oai/gnb.conf:/opt/oai-gnb/etc/gnb.conf" \
  -v "$PWD/configs/oai/neighbour-config-rfsim.conf:/opt/oai-gnb/etc/neighbour-config-rfsim.conf" \
  -e USE_ADDITIONAL_OPTIONS="--rfsim -E --gNBs.[0].min_rxtxtime 8" \
  oaisoftwarealliance/oai-gnb:develop

docker logs -f "$GNB_NAME"
