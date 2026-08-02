#!/usr/bin/env bash
set -euo pipefail

CONF_DIR=~/openairinterface5g/targets/PROJECTS/GENERIC-NR-5GC/CONF
UE_CONF=~/roaming-2core-lab/configs/oai/ue.conf
NET=open5gs-roaming-net
IMG=oai-ran-custom:local

echo "=== 1. Nettoyage des anciens conteneurs RAN (CU/DU/UE) ==="
docker rm -f cu du0 du1 oai-ue 2>/dev/null || true

echo "=== 2. Vérification que le core (vplmn/hplmn) et grafana tournent ==="
docker ps --format '{{.Names}}' | grep -E "vplmn-core|hplmn-core|grafana" || {
  echo "Core/Grafana non détectés, lance d'abord tes scripts existants :"
  echo "  ./02-start-cores.sh"
  echo "  docker start grafana   (si le conteneur existe déjà)"
  exit 1
}

echo "=== 3. Lancement du CU ==="
docker run -d --name cu \
  --network $NET --ip 172.18.0.30 \
  -p 9090:9090 \
  -v $CONF_DIR/gnb-cu.sa.f1.conf:/opt/oai-ran/gnb-cu.conf \
  $IMG \
  /opt/oai-ran/nr-softmodem -O /opt/oai-ran/gnb-cu.conf --telnetsrv --telnetsrv.shrmod ci

sleep 8

echo "=== 4. Lancement de l'UE (serveur RFsim) ==="
docker run -d --name oai-ue \
  --network $NET --ip 172.18.0.33 \
  --privileged \
  -v $UE_CONF:/opt/oai-ran/ue.conf \
  $IMG \
  /opt/oai-ran/nr-uesoftmodem -C 3450720000 -r 106 --numerology 1 --band 78 --ssb 516 --rfsim --rfsimulator.[0].serveraddr server -O /opt/oai-ran/ue.conf

sleep 8

echo "=== 5. Lancement de DU0 (PCI 0, avec telnet+chanmod) ==="
docker run -d --name du0 \
  --network $NET --ip 172.18.0.31 \
  -p 9091:9090 \
  -v $CONF_DIR/gnb-du.sa.band78.106prb.rfsim.pci0.conf:/opt/oai-ran/du0.conf \
  $IMG \
  /opt/oai-ran/nr-softmodem --rfsim -O /opt/oai-ran/du0.conf \
    --rfsimulator.[0].serveraddr 172.18.0.33 \
    --rfsimulator.[0].options chanmod \
    --gNBs.[0].min_rxtxtime 6 \
    --telnetsrv --telnetsrv.shrmod ci

sleep 15

echo "=== 6. Lancement de DU1 (PCI 1, avec telnet+chanmod) ==="
docker run -d --name du1 \
  --network $NET --ip 172.18.0.32 \
  -p 9092:9090 \
  -v $CONF_DIR/gnb-du.sa.band78.106prb.rfsim.pci1.conf:/opt/oai-ran/du1.conf \
  $IMG \
  /opt/oai-ran/nr-softmodem --rfsim -O /opt/oai-ran/du1.conf \
    --rfsimulator.[0].serveraddr 172.18.0.33 \
    --rfsimulator.[0].options chanmod \
    --gNBs.[0].min_rxtxtime 6 \
    --telnetsrv --telnetsrv.shrmod ci

echo "=== Terminé. Vérifie avec : docker ps -a ==="
