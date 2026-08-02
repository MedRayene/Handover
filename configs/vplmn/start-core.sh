#!/usr/bin/env bash
set -euo pipefail
mkdir -p /data/db /logs
cat /lab/configs/hosts.add >> /etc/hosts
mongod --dbpath /data/db --bind_ip 127.0.0.1 --fork --logpath /logs/mongo-vplmn.log
until mongosh --quiet --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
  echo "Waiting for MongoDB..."; sleep 1
done
cd /open5gs
pkill -9 open5gs || true
rm -f "${LOG_FILE:-/logs/vplmn.log}"
./build/tests/app/5gc -c "${CORE_CONFIG:-/lab/configs/5gc-vplmn.yaml}" > "${LOG_FILE:-/logs/vplmn.log}" 2>&1 &

sleep 2

cd /opt/prometheus/prometheus-3.5.0.linux-amd64

./prometheus \
  --config.file=/lab/configs/prometheus.yml \
  --web.listen-address=0.0.0.0:9095 &


tail -f "${LOG_FILE:-/logs/vplmn.log}"
