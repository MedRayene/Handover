#!/usr/bin/env bash
set -euo pipefail
mkdir -p /data/db /logs
cat /lab/configs/hosts.add >> /etc/hosts
mongod --dbpath /data/db --bind_ip 127.0.0.1 --fork --logpath /logs/mongo-hplmn.log
until mongosh --quiet --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
  echo "Waiting for MongoDB..."; sleep 1
done

mongosh open5gs --quiet --eval '
if (db.subscribers.countDocuments({imsi:"999700000000001"}) === 0) {
  db.subscribers.insertOne({
    imsi:"999700000000001",
    subscribed_rau_tau_timer:12,
    network_access_mode:0,
    subscriber_status:0,
    access_restriction_data:32,
    slice:[{
      sst:1, default_indicator:true,
      session:[{
        name:"internet", type:3, pcc_rule:[],
        ambr:{uplink:{value:1,unit:3},downlink:{value:1,unit:3}},
        qos:{index:9,arp:{priority_level:8,pre_emption_capability:1,pre_emption_vulnerability:1}}
      }]
    }],
    ambr:{uplink:{value:1,unit:3},downlink:{value:1,unit:3}},
    security:{k:"465B5CE8B199B49FAA5F0A2EE238A6BC",op:null,opc:"E8ED289DEBA952E4283B54E88E6183CA",amf:"8000"},
    schema_version:1, __v:0
  });
  print("Subscriber 999700000000001 provisioned.");
} else {
  print("Subscriber 999700000000001 already exists.");
}
'

cd /open5gs
pkill -9 open5gs || true
rm -f "${LOG_FILE:-/logs/hplmn.log}"
./build/tests/app/5gc -c "${CORE_CONFIG:-/lab/configs/5gc-hplmn.yaml}" > "${LOG_FILE:-/logs/hplmn.log}" 2>&1 &

tail -f "${LOG_FILE:-/logs/hplmn.log}"
