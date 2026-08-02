#!/usr/bin/env bash
set -euo pipefail
sudo sysctl -w kernel.sched_rt_runtime_us=-1
sudo sysctl -w net.ipv4.ip_forward=1
# Optional NAT for UE subnet; safe if rule already exists.
sudo iptables -t nat -C POSTROUTING -s 10.45.0.0/16 ! -o ogstun -j MASQUERADE 2>/dev/null || \
  sudo iptables -t nat -A POSTROUTING -s 10.45.0.0/16 ! -o ogstun -j MASQUERADE
