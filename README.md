# Roaming 5G Lab — Two Open5GS Cores (HPLMN + VPLMN) over SEPP

A minimal, standard **5G roaming testbed**. A subscriber from a Home network (HPLMN)
attaches through a Visited network (VPLMN), and the two cores exchange signalling over
the **SEPP** roaming interface — exactly like real inter-operator roaming.

```text
 OAI UE  ──►  OAI gNB  ──►  VPLMN core  ──(SEPP)──►  HPLMN core
(IMSI 999/70)  (PLMN 001/01)   AMF/SMF/SEPP          UDM/UDR/AUSF/SEPP
```

| Component   | Role                                             | PLMN     |
|-------------|--------------------------------------------------|----------|
| `hplmn-core`| Home network: UDM/UDR/AUSF + SEPP + MongoDB      | 999 / 70 |
| `vplmn-core`| Visited network: AMF/SMF/UPF + SEPP + MongoDB    | 001 / 01 |
| `oai-gnb`   | OAI gNB (rfsim) connected to the VPLMN AMF       | 001 / 01 |
| `oai-ue`    | OAI UE with a Home (HPLMN) SIM                    | 999 / 70 |

The subscriber SIM lives **only** in the HPLMN database, so a successful UE registration
proves the roaming (SEPP) path works end to end.

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
wsl                   # Simply open a new terminal and run wsl -> you are inside Ubuntu

docker version        # client + server both respond
docker compose version
```

> From here on, **run every command inside the Ubuntu/WSL terminal**, not PowerShell.

---

## 2. Get the lab

Copy this folder into your WSL home directory (recommended — much faster than `/mnt/c`):

```bash
cp -r "/mnt/c/Users/<you>/…/roaming-2core-lab" ~/roaming-2core-lab
cd ~/roaming-2core-lab
chmod +x scripts/*.sh
```

*(If you cloned it directly inside WSL with git, just `cd` into it and run the `chmod` line.)*

---

## 3. Run the testbed

Run the scripts in order from the lab directory.

### Step 0 — Host setup (once per boot)

Enables IP forwarding and NAT so the UE can reach the internet.

```bash
./scripts/00-host-setup.sh
```

### Step 1 — Build the core image (first time only, ~10–15 min)

Compiles Open5GS + MongoDB into a local image. Only needed the first time or after changing the Dockerfile.

```bash
./scripts/01-build-cores.sh
```

### Step 2 — Start the two cores

```bash
./scripts/02-start-cores.sh
```

Check both are up and the SEPP daemon is running:

```bash
docker ps                                  # expect hplmn-core and vplmn-core
docker exec hplmn-core ps aux | grep sepp  # expect open5gs-seppd
docker exec vplmn-core ps aux | grep sepp  # expect open5gs-seppd
```

The HPLMN core auto-provisions the subscriber (IMSI `999700000000001`) in its MongoDB on startup.

### Step 3 — Start the gNB

```bash
./scripts/03-start-gnb.sh        # follows the log; Ctrl+C to stop watching
```

Wait for:

```
Received NGSetupResponse
Running as server waiting opposite rfsimulators to connect
```

### Step 4 — Start the UE

In a new WSL terminal (`cd ~/roaming-2core-lab`):

```bash
./scripts/04-start-ue.sh         # follows the log; Ctrl+C to stop watching
```

Success looks like:

```
Registration Accept
PDU Session Establishment Accept
UE IPv4: 10.45.0.x
```

### Step 5 — Status check

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

---

## 5. Stop / clean up

```bash
./scripts/99-clean.sh            # removes UE, gNB, both cores and the network
```

To also remove unused Docker networks:

```bash
docker network prune -f
```

To rerun after cleaning, start again from **Step 2** (no rebuild needed).
A quick rerun cheat-sheet is in [RERUN.md](RERUN.md).

---

## Layout

```
roaming-2core-lab/
├── .env                     # network name, subnet, container names
├── docker-compose.yml       # hplmn-core + vplmn-core + roaming bridge network
├── docker/open5gs-core/     # Dockerfile: Open5GS + MongoDB image
├── configs/
│   ├── hplmn/               # HPLMN 5GC yaml, start script, subscriber provisioning
│   ├── vplmn/               # VPLMN 5GC yaml, start script
│   └── oai/                 # gNB + UE configs (gnb.conf, ue.conf, neighbour-config)
├── scripts/                 # 00–05 run flow + 99 cleanup
└── logs/                    # core + MongoDB logs (mounted from the containers)
```

## Subscriber (Home SIM)

| Field | Value |
|-------|-------|
| IMSI  | `999700000000001` |
| Key   | `465B5CE8B199B49FAA5F0A2EE238A6BC` |
| OPc   | `E8ED289DEBA952E4283B54E88E6183CA` |
| DNN   | `internet` (SST 1) |

These values are identical in the HPLMN database and in `configs/oai/ue.conf` — if you
change one, change the other.

## Troubleshooting

- **UE stuck / no Registration Accept** → confirm SEPP is running in *both* cores (Step 2)
  and check `logs/hplmn.log` and `logs/vplmn.log`.
- **gNB never prints NGSetupResponse** → the VPLMN AMF isn't reachable; make sure Step 2
  finished and `docker ps` shows `vplmn-core`.
- **`configs/oai/*.conf` errors in Step 3** → the file must exist as a *file*; if Docker
  ever created it as an empty directory, delete it and restore the config.
- **Permission errors on scripts** → `chmod +x scripts/*.sh`.
