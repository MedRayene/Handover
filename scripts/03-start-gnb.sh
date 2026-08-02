#!/usr/bin/env bash
set -euo pipefail

source .env

# Vérification des fichiers
for cfg in configs/oai/gnb1.conf configs/oai/gnb2.conf configs/oai/neighbour-config-rfsim.conf
do
    if [ ! -f "$PWD/$cfg" ]; then
        echo "$cfg introuvable"
        exit 1
    fi
done

docker rm -f gnb1 2>/dev/null || true
docker rm -f gnb2 2>/dev/null || true

########################################
# gNB1
########################################

docker run -d \
    --name gnb1 \
    --hostname gnb1 \
    --network "$NET_NAME" \
    --privileged \
    -p 9090:9090 \
    -v "$PWD/configs/oai/gnb1.conf:/opt/oai-gnb/etc/gnb.conf" \
    -v "$PWD/configs/oai/neighbour-config-rfsim.conf:/opt/oai-gnb/etc/neighbour-config-rfsim.conf" \
    -e USE_ADDITIONAL_OPTIONS="--rfsim -E --gNBs.[0].min_rxtxtime 8 --telnetsrv" \
    oaisoftwarealliance/oai-gnb:develop

########################################
# gNB2
########################################

docker run -d \
    --name gnb2 \
    --hostname gnb2 \
    --network "$NET_NAME" \
    --privileged \
    -v "$PWD/configs/oai/gnb2.conf:/opt/oai-gnb/etc/gnb.conf" \
    -v "$PWD/configs/oai/neighbour-config-rfsim.conf:/opt/oai-gnb/etc/neighbour-config-rfsim.conf" \
    -e USE_ADDITIONAL_OPTIONS="--rfsim -E --gNBs.[0].min_rxtxtime 8" \
    oaisoftwarealliance/oai-gnb:develop

echo ""
echo "Les deux gNB sont démarrés."
echo ""

docker ps | grep gnb
