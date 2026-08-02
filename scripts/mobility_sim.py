#!/usr/bin/env python3
"""
Simulateur de mobilité UE entre DU0 (gNB1) et DU1 (gNB2).
Utilise telnetlib (gère la négociation du protocole telnet, contrairement
à un socket brut) pour envoyer des commandes channelmod réelles.
"""

import telnetlib
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

DU0_HOST, DU0_PORT = "localhost", 9091
DU1_HOST, DU1_PORT = "localhost", 9092
CHANNEL_ID = 0

PLOSS_MIN = 0
PLOSS_MAX = 45
STEP_DB = 1
STEP_INTERVAL_S = 3

METRICS_PORT = 9093
PROMPT = b"softmodem_gnb>"

state_lock = threading.Lock()
state = {"ploss_du0": PLOSS_MIN, "ploss_du1": PLOSS_MAX, "direction": "du0_to_du1"}


def connect(host, port):
    tn = telnetlib.Telnet(host, port, timeout=5)
    tn.read_until(PROMPT, timeout=5)  # avale le banner + premier prompt
    return tn


def set_ploss(tn, value_db):
    cmd = f"channelmod modify {CHANNEL_ID} ploss {value_db}\n"
    tn.write(cmd.encode())
    return tn.read_until(PROMPT, timeout=3).decode(errors="ignore")


def mobility_loop():
    print("Connexion telnet a DU0 et DU1...")
    tn_du0 = connect(DU0_HOST, DU0_PORT)
    tn_du1 = connect(DU1_HOST, DU1_PORT)
    print("Connecte. Demarrage de la boucle de mobilite.")

    while True:
        with state_lock:
            state["direction"] = "du0_to_du1"
        for ploss in range(PLOSS_MIN, PLOSS_MAX + 1, STEP_DB):
            resp0 = set_ploss(tn_du0, ploss)
            resp1 = set_ploss(tn_du1, PLOSS_MAX - ploss)
            with state_lock:
                state["ploss_du0"] = ploss
                state["ploss_du1"] = PLOSS_MAX - ploss
            print(f"[ALLER] du0={ploss}dB du1={PLOSS_MAX - ploss}dB "
                  f"| confirme du0: {'path loss: ' + str(float(ploss)) in resp0}")
            time.sleep(STEP_INTERVAL_S)
        time.sleep(5)

        with state_lock:
            state["direction"] = "du1_to_du0"
        for ploss in range(PLOSS_MIN, PLOSS_MAX + 1, STEP_DB):
            resp1 = set_ploss(tn_du1, ploss)
            resp0 = set_ploss(tn_du0, PLOSS_MAX - ploss)
            with state_lock:
                state["ploss_du1"] = ploss
                state["ploss_du0"] = PLOSS_MAX - ploss
            print(f"[RETOUR] du1={ploss}dB du0={PLOSS_MAX - ploss}dB")
            time.sleep(STEP_INTERVAL_S)
        time.sleep(5)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with state_lock:
            d0, d1 = state["ploss_du0"], state["ploss_du1"]
        body = (
            "# HELP mobility_sim_pathloss_db Path loss RF simule (dB)\n"
            "# TYPE mobility_sim_pathloss_db gauge\n"
            f'mobility_sim_pathloss_db{{cell="du0_gnb1"}} {d0}\n'
            f'mobility_sim_pathloss_db{{cell="du1_gnb2"}} {d1}\n'
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
    print(f"Exporteur Prometheus demarre sur :{METRICS_PORT}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    main()
