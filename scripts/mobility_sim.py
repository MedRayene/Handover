#!/usr/bin/env python3
"""
Simulateur de mobilite UE entre DU0 (gNB1) et DU1 (gNB2), avec handover F1
declenche et confirme automatiquement au croisement des courbes de path loss.
"""

import telnetlib
import time
import threading
import subprocess
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

DU0_HOST, DU0_PORT = "localhost", 9091
DU1_HOST, DU1_PORT = "localhost", 9092
CU_HOST, CU_PORT = "localhost", 9090
DU_CONTAINERS = {"du0": "du0", "du1": "du1"}
CHANNEL_ID = 0

PLOSS_MIN = 0
PLOSS_MAX = 45
STEP_DB = 1
STEP_INTERVAL_S = 3

METRICS_PORT = 9093
PROMPT = b"softmodem_gnb>"

state_lock = threading.Lock()
state = {"ploss_du0": PLOSS_MIN, "ploss_du1": PLOSS_MAX, "direction": "du0_to_du1"}

handover_lock = threading.Lock()
handover_state = {
    "served_by": "du0",
    "triggered_total": 0,
    "confirmed_total": 0,
    "failed_total": 0,
    "last_status": "idle",
}


def connect(host, port):
    tn = telnetlib.Telnet(host, port, timeout=5)
    tn.read_until(PROMPT, timeout=5)
    return tn


def set_ploss(tn, value_db):
    cmd = f"channelmod modify {CHANNEL_ID} ploss {value_db}\n"
    tn.write(cmd.encode())
    return tn.read_until(PROMPT, timeout=3).decode(errors="ignore")


def docker_logs_since(container, since_iso):
    try:
        result = subprocess.run(
            ["docker", "logs", "--since", since_iso, container],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout + result.stderr
    except Exception as e:
        print(f"[WARN] docker logs failed for {container}: {e}", flush=True)
        return ""


def try_start_handover():
    """Verifie la condition et reserve atomiquement le HO (evite le double trigger)."""
    with handover_lock:
        source = handover_state["served_by"]
        target = "du1" if source == "du0" else "du0"
        with state_lock:
            crossed = (
                (source == "du0" and state["ploss_du1"] < state["ploss_du0"])
                or (source == "du1" and state["ploss_du0"] < state["ploss_du1"])
            )
        if not crossed or handover_state["last_status"] == "pending":
            return
        handover_state["last_status"] = "pending"
        handover_state["triggered_total"] += 1

    threading.Thread(target=run_handover, args=(source, target), daemon=True).start()


def run_handover(source, target):
    trigger_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[HO] Declenchement handover {source} -> {target}", flush=True)
    try:
        subprocess.run(
            f'echo "ci trigger_f1_ho" | nc -q 1 {CU_HOST} {CU_PORT}',
            shell=True, timeout=5, capture_output=True
        )
    except Exception as e:
        print(f"[HO] Erreur envoi trigger: {e}", flush=True)
        with handover_lock:
            handover_state["last_status"] = "failed"
            handover_state["failed_total"] += 1
        return

    source_released = False
    target_active = False
    deadline = time.time() + 10
    while time.time() < deadline:
        time.sleep(1)
        if not source_released:
            logs = docker_logs_since(DU_CONTAINERS[source], trigger_time)
            if "Remove NR rnti" in logs:
                source_released = True
        if not target_active:
            logs = docker_logs_since(DU_CONTAINERS[target], trigger_time)
            if "in-sync" in logs:
                target_active = True
        if source_released and target_active:
            break

    with handover_lock:
        if source_released and target_active:
            handover_state["served_by"] = target
            handover_state["confirmed_total"] += 1
            handover_state["last_status"] = "success"
            print(f"[HO] Confirme: UE maintenant servi par {target}", flush=True)
        else:
            handover_state["failed_total"] += 1
            handover_state["last_status"] = "failed"
            print(f"[HO] Echec/non confirme (source_released={source_released}, target_active={target_active})", flush=True)


def mobility_loop():
    print("Connexion telnet a DU0 et DU1...", flush=True)
    tn_du0 = connect(DU0_HOST, DU0_PORT)
    tn_du1 = connect(DU1_HOST, DU1_PORT)
    print("Connecte. Demarrage de la boucle de mobilite.", flush=True)

    while True:
        with state_lock:
            state["direction"] = "du0_to_du1"
        for ploss in range(PLOSS_MIN, PLOSS_MAX + 1, STEP_DB):
            set_ploss(tn_du0, ploss)
            set_ploss(tn_du1, PLOSS_MAX - ploss)
            with state_lock:
                state["ploss_du0"] = ploss
                state["ploss_du1"] = PLOSS_MAX - ploss
            print(f"[ALLER] du0={ploss}dB du1={PLOSS_MAX - ploss}dB", flush=True)
            time.sleep(STEP_INTERVAL_S)
            try_start_handover()

        time.sleep(5)

        with state_lock:
            state["direction"] = "du1_to_du0"
        for ploss in range(PLOSS_MIN, PLOSS_MAX + 1, STEP_DB):
            set_ploss(tn_du1, ploss)
            set_ploss(tn_du0, PLOSS_MAX - ploss)
            with state_lock:
                state["ploss_du1"] = ploss
                state["ploss_du0"] = PLOSS_MAX - ploss
            print(f"[RETOUR] du1={ploss}dB du0={PLOSS_MAX - ploss}dB", flush=True)
            time.sleep(STEP_INTERVAL_S)
            try_start_handover()

        time.sleep(5)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with state_lock:
            d0, d1 = state["ploss_du0"], state["ploss_du1"]
            direction_code = 0 if state["direction"] == "du0_to_du1" else 1
        with handover_lock:
            served_code = 0 if handover_state["served_by"] == "du0" else 1
            triggered = handover_state["triggered_total"]
            confirmed = handover_state["confirmed_total"]
            failed = handover_state["failed_total"]
            status_map = {"idle": 0, "pending": 1, "success": 2, "failed": 3}
            status_code = status_map[handover_state["last_status"]]
        body = (
            "# HELP mobility_sim_pathloss_db Path loss RF simule (dB)\n"
            "# TYPE mobility_sim_pathloss_db gauge\n"
            f'mobility_sim_pathloss_db{{cell="du0_gnb1"}} {d0}\n'
            f'mobility_sim_pathloss_db{{cell="du1_gnb2"}} {d1}\n'
            "# HELP mobility_direction_code Sens du deplacement (0=du0->du1, 1=du1->du0)\n"
            "# TYPE mobility_direction_code gauge\n"
            f'mobility_direction_code {direction_code}\n'
            "# HELP serving_cell_code Cellule confirmee servant l'UE (0=du0, 1=du1)\n"
            "# TYPE serving_cell_code gauge\n"
            f'serving_cell_code {served_code}\n'
            "# HELP handover_triggered_total Nombre de commandes de handover envoyees\n"
            "# TYPE handover_triggered_total counter\n"
            f'handover_triggered_total {triggered}\n'
            "# HELP handover_confirmed_total Nombre de handovers confirmes par les logs DU\n"
            "# TYPE handover_confirmed_total counter\n"
            f'handover_confirmed_total {confirmed}\n'
            "# HELP handover_failed_total Nombre de handovers non confirmes/echoues\n"
            "# TYPE handover_failed_total counter\n"
            f'handover_failed_total {failed}\n'
            "# HELP handover_last_status Dernier statut (0=idle,1=pending,2=success,3=failed)\n"
            "# TYPE handover_last_status gauge\n"
            f'handover_last_status {status_code}\n'
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass


def main():
    threading.Thread(target=mobility_loop, daemon=True).start()
    server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
    print(f"Exporteur Prometheus demarre sur :{METRICS_PORT}/metrics", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
