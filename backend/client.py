"""
Flower client for federated threat detection.

Each client represents one organisation with its own local data partition.
Only model parameters (weight updates) are sent to the server -- 
never raw data.

Usage:
    python -m client --partition 0
    python -m client --partition 1
    python -m client --partition 2
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

import flwr as fl
import numpy as np

# Ensure the app package is importable
sys.path.insert(0, ".")

from app.ml.data import load_partition
from app.ml.model import ThreatNet, get_parameters, set_parameters, train_model, test_model

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [Client] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ORG_NAMES = {
    0: "Organization Alpha",
    1: "Organization Beta",
    2: "Organization Gamma",
}
ORG_IDS = {
    0: "org-alpha",
    1: "org-beta",
    2: "org-gamma",
}


class ThreatDetectionClient(fl.client.NumPyClient):
    """Flower NumPy client wrapping ThreatNet."""

    def __init__(self, partition_id: int) -> None:
        self.partition_id = partition_id
        self.org_name = ORG_NAMES.get(partition_id, f"Organization {partition_id}")
        self.org_id = ORG_IDS.get(partition_id, f"org-{partition_id}")
        self.model = ThreatNet()
        self.train_loader, self.test_loader, self.num_train = load_partition(
            partition_id=partition_id,
            num_partitions=3,
        )
        logger.info(
            f"Initialised {self.org_name} (partition {partition_id}) "
            f"with {self.num_train} training samples"
        )

    def get_parameters(self, config: dict) -> list[np.ndarray]:
        return get_parameters(self.model)

    def fit(
        self, parameters: list[np.ndarray], config: dict
    ) -> tuple[list[np.ndarray], int, dict]:
        """Receive global model, train locally, return updated weights."""
        set_parameters(self.model, parameters)

        epochs = config.get("local_epochs", 1)
        start = time.time()
        avg_loss, num_samples = train_model(
            self.model, self.train_loader, epochs=epochs
        )
        duration = time.time() - start

        # Evaluate after local training
        loss, accuracy, f1, _ = test_model(self.model, self.test_loader)

        logger.info(
            f"[{self.org_name}] Round fit complete: "
            f"loss={loss:.4f}, acc={accuracy:.4f}, f1={f1:.4f}, "
            f"duration={duration:.1f}s"
        )

        return get_parameters(self.model), num_samples, {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "partition_id": self.partition_id,
            "local_accuracy": float(accuracy),
            "local_loss": float(loss),
            "local_f1": float(f1),
            "samples_used": num_samples,
            "duration_s": round(duration, 1),
        }

    def evaluate(
        self, parameters: list[np.ndarray], config: dict
    ) -> tuple[float, int, dict]:
        """Evaluate the global model on local test data."""
        set_parameters(self.model, parameters)
        loss, accuracy, f1, num_samples = test_model(self.model, self.test_loader)

        logger.info(
            f"[{self.org_name}] Evaluate: loss={loss:.4f}, "
            f"acc={accuracy:.4f}, f1={f1:.4f}"
        )

        return float(loss), num_samples, {
            "org_id": self.org_id,
            "accuracy": float(accuracy),
            "f1": float(f1),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Flower FL Client")
    parser.add_argument(
        "--partition", type=int, required=True,
        help="Data partition ID (0, 1, or 2)",
    )
    parser.add_argument(
        "--server", type=str, default="127.0.0.1:8080",
        help="Flower server address (default: 127.0.0.1:8080)",
    )
    args = parser.parse_args()

    client = ThreatDetectionClient(partition_id=args.partition)
    fl.client.start_client(
        server_address=args.server,
        client=client.to_client(),
    )


if __name__ == "__main__":
    main()
