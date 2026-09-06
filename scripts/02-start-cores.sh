#!/bin/bash
echo "Starting 5G Core and Grafana..."
docker compose up -d vplmn-core grafana
echo ""
echo "=== VPLMN logs ==="
docker logs --tail 20 vplmn-core
echo ""
echo "=== Grafana logs ==="
docker logs --tail 20 grafana
echo ""
echo "Containers started successfully."
echo ""
echo "Dashboard:"
echo "  Grafana : http://localhost:3000"
echo ""
echo "Useful commands:"
echo "docker logs -f vplmn-core"
echo "docker logs -f grafana"
