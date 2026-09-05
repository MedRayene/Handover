#!/usr/bin/env bash
set -euo pipefail
docker exec vplmn-core /open5gs/build/misc/db/open5gs-dbctl \
  add 001010000000001 465B5CE8B199B49FAA5F0A2EE238A6BC E8ED289DEBA952E4283B54E88E6183CA
