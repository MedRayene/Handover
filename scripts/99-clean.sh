#!/usr/bin/env bash
set -euo pipefail

# Stop RAN and UE containers
docker rm -f oai-ue oai-gnb 2>/dev/null || true

# Stop and remove core network containers + networks
docker compose down
