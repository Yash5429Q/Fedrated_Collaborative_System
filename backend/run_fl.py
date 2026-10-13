"""
Convenience script to run the full federated learning pipeline.

Starts the Flower server, waits briefly, then spawns 3 client processes.
Use this for quick demos / local testing.

Usage:
    python run_fl.py
    python run_fl.py --rounds 3
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import os

PYTHON = os.path.join("venv", "Scripts", "python.exe") if os.name == "nt" else sys.executable


def main() -> None:
    parser = argparse.ArgumentParser(description="Run federated learning pipeline")
    parser.add_argument("--rounds", type=int, default=5, help="Number of FL rounds")
    parser.add_argument("--clients", type=int, default=3, help="Number of clients")
    args = parser.parse_args()

    print(f"=== Starting Federated Learning Pipeline ===")
    print(f"  Rounds: {args.rounds}")
    print(f"  Clients: {args.clients}")
    print()

    # 1. Start Flower server
    print("[1/2] Starting Flower server...")
    server_proc = subprocess.Popen(
        [
            PYTHON, "server.py",
            "--rounds", str(args.rounds),
            "--min-clients", str(args.clients),
        ],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Give server time to start listening
    time.sleep(3)

    # 2. Start clients
    print(f"[2/2] Starting {args.clients} clients...")
    client_procs = []
    for i in range(args.clients):
        proc = subprocess.Popen(
            [
                PYTHON, "client.py",
                "--partition", str(i),
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        client_procs.append(proc)
        time.sleep(0.5)  # Stagger slightly

    # Wait for all processes
    print("\nWaiting for federated training to complete...\n")
    server_proc.wait()

    for proc in client_procs:
        proc.wait()

    print("\n=== Federated Learning Pipeline Complete ===")


if __name__ == "__main__":
    main()
