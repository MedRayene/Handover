# Roaming 5G Lab — CU/DU Mobility & Real F1 Handover over Two Open5GS Cores

A 5G Standalone testbed built on top of a **two-core roaming lab** (HPLMN + VPLMN over
SEPP) that has been extended with a **CU/DU radio architecture** (OpenAirInterface,
RF Simulator) to demonstrate **real UE mobility and a real F1 handover** between two
cells — not a simulated re-attach. The UE's radio channel is driven live via OAI's
embedded telnet interface, and a real handover is triggered and confirmed (via
log-based proof) as the UE moves from one cell to the other. Everything is exported to
Prometheus and visualized in a dedicated Grafana dashboard.

**Repository:** [tahangz/testbed-Roaming-Open5gs](https://github.com/tahangz/testbed-Roaming-Open5gs)

```text
[NWDAF-ready core]
 OAI UE  ◄──rfsim──►  DU0 / DU1  ──F1──►  CU  ──N2──►  VPLMN core  ──(SEPP)──►  HPLMN core
(IMSI 001/01 native)   (PLMN 001/01)              AMF/SMF/UPF                UDM/UDR/AUSF
                                                                              (roaming, optional)
```

| Component     | Role                                                          | PLMN     |
|---------------|----------------------------------------------------------------|----------|
| `hplmn-core`  | Home network: UDM/UDR/AUSF + SEPP + MongoDB                    | 999 / 70 |
| `vplmn-core`  | Visited network: AMF/SMF/UPF + SEPP + MongoDB + Prometheus      | 001 / 01 |
| `cu`          | OAI CU (RRC/PDCP), N2 connection to the VPLMN AMF               | 001 / 01 |
| `du0` / `du1` | OAI DUs (RLC/MAC/PHY), one cell each, F1 to the CU, telnet control | 001 / 01 |
| `oai-ue`      | OAI UE, RFsimulator **server** (DUs connect to it as clients)   | 001 / 01 |
| `grafana`     | Dashboards: core NF health + mobility/handover KPIs             | —        |

The default subscriber used for the mobility scenario is now **native to the VPLMN**
(IMSI prefix `001/01`), so the UE attaches and moves between DU0/DU1 entirely inside
the VPLMN, without depending on the HPLMN. The original roaming path (HPLMN subscriber,
SEPP) documented in earlier versions of this lab is still available as a separate
scenario if you need to demonstrate inter-operator roaming specifically — see
[Troubleshooting](#troubleshooting) for how the two scenarios differ.

---

## 1. Prerequisites (Windows, from zero)

This lab runs on Linux containers. On Windows the supported path is **WSL2 + Docker Desktop**.

### 1.1 Install WSL2 (Ubuntu)

Open **PowerShell as Administrator** and run:

```powershell
wsl --install -d Ubuntu
```

Reboot if prompted, then launch **Ubuntu** from the Start menu and create your Linux
username/password when asked. Confirm you are on WSL2:

```powershell
wsl -l -v      # STATE should be "Running", VERSION should be "2"
```

### 1.2 Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. Install it, then start it.
3. In **Settings → General**, enable **Use the WSL 2 based engine**.
4. In **Settings → Resources → WSL Integration**, enable integration for your **Ubuntu** distro.
5. Apply & Restart.

Verify from **inside the Ubuntu (WSL) terminal**:

```bash
wsl                   # open a new terminal and run wsl -> you are inside Ubuntu

docker version        # client + server both respond
docker compose version
```

> From here on, **run every command inside the Ubuntu/WSL terminal**, not PowerShell.
> Also make sure your Windows clock is correctly synced (`Settings > Date & time >
> Sync now`) — a drifted host clock breaks Grafana's time range queries in ways that
> look like a Prometheus problem but aren't (see Troubleshooting).

---

## 2. Get the lab

Clone the repository into your WSL home directory (recommended — much faster than `/mnt/c`):

```bash
sudo apt-get update && sudo apt-get install -y git   # if git isn't installed yet
cd ~
git clone https://github.com/tahangz/testbed-Roaming-Open5gs.git roaming-2core-lab
cd roaming-2core-lab
chmod +x scripts/*.sh
```

> This is a **private** repo — when prompted, sign in with your GitHub account (or a
> Personal Access Token as the password).

Note: the RAN binaries (`nr-softmodem`, `nr-uesoftmodem`) are **not** stored in this
repository. The `docker/oai-custom/Dockerfile` compiles OpenAirInterface from source
(a fixed, known-good commit) as part of the image build — see Step 3 below. This keeps
the repository lightweight and guarantees a fully reproducible build on any machine.

---

## 3. Run the testbed

Run the scripts in order from the lab directory.

### Step 0 — Host setup (once per boot)

Enables IP forwarding and NAT so the UE can reach the internet.

```bash
./scripts/00-host-setup.sh
```

### Step 1 — Build the core image (first time only, ~10–15 min)

```bash
./scripts/01-build-cores.sh
```

### Step 2 — Build the RAN image (first time only, ~30–50 min)

Compiles OpenAirInterface (gNB + UE binaries, with the embedded telnet server used for
mobility/handover control) from source into a local image.

```bash
docker build -t oai-ran-custom:local docker/oai-custom/
```

### Step 3 — Start the two cores

```bash
./scripts/02-start-cores.sh
```

Check both are up:

```bash
docker ps                                  # expect hplmn-core and vplmn-core
```

### Step 4 — Provision the native VPLMN subscriber (first time only)

```bash
./scripts/02b-seed-subscriber.sh
```

### Step 5 — Start the CU/DU/UE chain

```bash
./scripts/06-start-cudu-lab.sh
```

Wait ~30–40 s, then check the full chain is up:

```bash
docker ps -a       # expect cu, du0, du1, oai-ue all "Up"
docker logs oai-ue | grep -E "Registration Accept|PDU Session Establishment"
```

Success looks like:

```
Received Registration Accept with result 3GPP
Received PDU Session Establishment Accept, UE IPv4: 10.46.0.x
```

### Step 6 — Start the mobility & handover simulator

Drives the UE's simulated radio channel between DU0 and DU1, and triggers/confirms a
real F1 handover at the crossover point.

```bash
cd scripts
nohup python3 -u mobility_sim.py > mobility_sim.log 2>&1 &
cd ..
```

Check it's exporting metrics:

```bash
curl -s localhost:9093/metrics | head -20
```

### Step 7 — Import the Grafana dashboard

1. Open `http://localhost:3000`
2. Add two Prometheus data sources if not already present: `vplmn` → `http://vplmn-core:9095` (default), `hplmn` → `http://hplmn-core:9095`
3. **Dashboards → Import** → paste the contents of `configs/grafana/mobility-dashboard.json`

### Step 8 — Status check

```bash
./scripts/05-status.sh
```

---

## 4. Test data connectivity (optional)

```bash
# Find the UE's tunnel interface and IP
docker exec oai-ue ip a | grep oaitun

# Ping out through the UE tunnel
docker exec oai-ue ping -I oaitun_ue1 -c 4 8.8.8.8
```

## 5. Test the handover manually (optional)

```bash
echo "ci trigger_f1_ho" | nc -q 1 localhost 9090
docker logs --tail 20 du0   # source: should show "Remove NR rnti"
docker logs --tail 20 du1   # target: should show a new active "in-sync" session
```

---

## 6. Stop / clean up

```bash
pkill -f mobility_sim.py
./scripts/99-clean.sh            # removes UE, DU0, DU1, CU, both cores and the network
```

To also remove unused Docker networks:

```bash
docker network prune -f
```

To rerun after cleaning, start again from **Step 3** (no rebuild needed, unless you
also removed the images).

---

## Layout

```
roaming-2core-lab/
├── .env                       # network name, subnet, container names
├── docker-compose.yml         # legacy monolithic gNB scenario (see Troubleshooting)
├── docker/
│   ├── open5gs-core/          # Dockerfile: Open5GS + MongoDB image
│   └── oai-custom/            # Dockerfile: compiles OAI CU/DU/UE from source
├── configs/
│   ├── hplmn/                 # HPLMN 5GC yaml, start script, Prometheus config
│   ├── vplmn/                 # VPLMN 5GC yaml, start script, Prometheus config
│   ├── oai/                   # legacy monolithic gNB/UE configs
│   └── grafana/               # exportable dashboard JSON
├── scripts/                   # 00–06 run flow, 02b subscriber seed, 99 cleanup, mobility_sim.py
└── logs/                      # core + MongoDB logs (mounted from the containers)
```

## Subscriber

### Native VPLMN subscriber (used by the CU/DU mobility scenario, Steps 4–6 above)

| Field | Value |
|-------|-------|
| IMSI  | `001010000000001` |
| Key   | `465B5CE8B199B49FAA5F0A2EE238A6BC` |
| OPc   | `E8ED289DEBA952E4283B54E88E6183CA` |
| DNN   | `internet` (SST 1) |

### Legacy roaming subscriber (Home SIM, HPLMN — original scenario, monolithic gNB)

| Field | Value |
|-------|-------|
| IMSI  | `999700000000001` |
| Key   | `465B5CE8B199B49FAA5F0A2EE238A6BC` |
| OPc   | `E8ED289DEBA952E4283B54E88E6183CA` |
| DNN   | `internet` (SST 1) |

These values must stay identical between the relevant core database and the matching
`ue.conf` — if you change one, change the other.

## Troubleshooting

- **No handover confirmation (`handover_failed_total` increasing)** → check that both
  `du0` and `du1` are `Up` and that the CU's telnet port (9090) is reachable
  (`telnet localhost 9090`). A handover can only be confirmed if the source DU logs
  `Remove NR rnti` and the target DU logs a new `in-sync` session within 10 s.
- **Grafana shows "No data" on every panel, including previously working ones** →
  check your **host clock** first (`date` in WSL vs. the Windows clock). A drifted host
  clock desyncs the time range Grafana's browser sends, even though Prometheus itself
  is healthy. Fix the Windows clock, then `wsl --shutdown` from PowerShell and restart
  everything.
- **RSRP-based metrics look flat / not meaningful** → this is expected with this
  RFsimulator setup: `max_rxgain` compensates path loss over most of the usable range,
  so RSRP saturates. Use the **Real SNR** panel instead (uplink SNR parsed from PHY
  logs), which does reflect real degradation.
- **Two subscribers, one testbed** → the monolithic `gnb1`/`gnb2` scenario (roaming,
  HPLMN SIM) and the CU/DU mobility scenario (native VPLMN SIM) are independent; don't
  run both RAN stacks at the same time on the same core.
- **UE stuck / no Registration Accept** → confirm the core is up and the subscriber
  exists in the right database (`docker exec vplmn-core mongosh --quiet --eval
  'db.getSiblingDB("open5gs").subscribers.find({"imsi":"<IMSI>"})'`).
- **`docker build` fails cloning OpenAirInterface** → the clone can be interrupted on
  slow connections; the Dockerfile uses `--depth 1` and increased Git buffers to
  mitigate this, but a retry (`docker build` again) usually resolves a one-off network
  glitch, resuming from Docker's build cache.
- **Permission errors on scripts** → `chmod +x scripts/*.sh`.
