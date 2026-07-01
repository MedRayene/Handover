#!/bin/bash

docker compose up -d hplmn-core vplmn-core

echo "=== HPLMN logs ==="
docker logs --tail 20 hplmn-core

echo ""
echo "=== VPLMN logs ==="
docker logs --tail 20 vplmn-core

echo ""
echo "Containers started successfully."
echo ""
echo "Follow logs manually with:"
echo "docker logs -f hplmn-core"
echo "docker logs -f vplmn-core"