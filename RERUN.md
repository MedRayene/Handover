# Roaming Open5GS Lab Setup

## Clean Previous Containers

Stop and remove all existing containers:

```bash
docker rm -f oai-ue oai-gnb hplmn-core vplmn-core 2>/dev/null || true
```

Optional: verify that no containers remain:

```bash
docker ps -a
```

Optional: remove unused Docker networks:

```bash
docker network prune -f
```

After cleaning, rerun the setup in the correct order.

---

# 1. Start Core Networks

Go to the lab directory:

```bash
cd ~/roaming-2core-lab
```

Start the HPLMN and VPLMN cores:

```bash
./scripts/02-start-cores.sh
```

Verify that the containers are running:

```bash
docker ps
```

You should see:

* `hplmn-core`
* `vplmn-core`

---

## Verify SEPP

Check that the SEPP process is running inside both cores:

```bash
docker exec hplmn-core ps aux | grep sepp
docker exec vplmn-core ps aux | grep sepp
```

Expected output:

```bash
open5gs-seppd
```

---

# 2. Start the gNB

Start the gNB:

```bash
./scripts/03-start-gnb.sh
```

Follow the gNB logs:

```bash
docker logs -f oai-gnb
```

Wait until the following messages appear:

```text
Received NGSetupResponse
Running as server waiting opposite rfsimulators to connect
```

---

# 3. Start the UE

Start the UE:

```bash
./scripts/04-start-ue.sh
```

Follow the UE logs:

```bash
docker logs -f oai-ue
```

Expected successful registration:

```text
Registration Accept
PDU Session Establishment Accept
UE IPv4: 10.45.0.x
```

---

# Expected Result

If everything is working correctly:

* Both HPLMN and VPLMN cores are running
* SEPP is active in both networks
* gNB successfully connects to the AMF
* UE successfully registers
* PDU session is established
* UE receives an IPv4 address
