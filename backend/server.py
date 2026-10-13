"""
Flower server for federated threat detection.

Runs FedAvg aggregation over N rounds, then persists each round's
metrics into the SQLite database so the FastAPI backend can serve
real training data.

Usage:
    python -m server --rounds 5 --min-clients 3
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

import flwr as fl
import numpy as np
from flwr.common import (
    FitRes,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy

# Ensure the app package is importable
sys.path.insert(0, ".")

from app.ml.model import ThreatNet, get_parameters, set_parameters, test_model
from app.ml.data import load_partition

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [Server] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Get the current max round from the DB ──────────────────────

def _get_max_round_from_db() -> int:
    """Query DB for the highest existing round_number. Returns 0 if empty."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_async_get_max_round())
        loop.close()
        return result
    except Exception as e:
        logger.warning(f"Could not read max round from DB: {e}")
        return 0


async def _async_get_max_round() -> int:
    from app.database.session import AsyncSessionLocal
    from app.models.training_round import TrainingRound
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.max(TrainingRound.round_number))
        )
        val = result.scalar_one_or_none()
        return val if val is not None else 0


# ── Database persistence ───────────────────────────────────────

def _save_round_to_db(
    round_number: int,
    global_accuracy: float,
    global_loss: float,
    global_f1: float,
    duration_s: int,
    num_clients: int,
    total_clients: int,
    client_metrics: list[dict],
) -> None:
    """
    Persist one federated round and per-client results into the database.
    Uses a new event loop since Flower callbacks are synchronous.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _async_save_round(
                round_number, global_accuracy, global_loss, global_f1,
                duration_s, num_clients, total_clients, client_metrics,
            )
        )
        loop.close()
    except Exception as e:
        logger.error(f"Failed to save round {round_number} to DB: {e}")


async def _async_save_round(
    round_number: int,
    global_accuracy: float,
    global_loss: float,
    global_f1: float,
    duration_s: int,
    num_clients: int,
    total_clients: int,
    client_metrics: list[dict],
) -> None:
    """Async helper that writes round data using our existing ORM models."""
    from app.database.session import AsyncSessionLocal
    from app.models.training_round import TrainingRound
    from app.models.client_participation import ClientParticipation
    from sqlalchemy import select

    now = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as session:
        # Check if this round already exists (idempotent)
        result = await session.execute(
            select(TrainingRound).where(TrainingRound.round_number == round_number)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing round
            existing.status = "completed"
            existing.accuracy = global_accuracy
            existing.loss = global_loss
            existing.f1 = global_f1
            existing.duration_s = duration_s
            existing.participating_clients = num_clients
            existing.completed_at = now
            round_id = existing.id
        else:
            # Insert new round
            tr = TrainingRound(
                round_number=round_number,
                status="completed",
                started_at=now,
                completed_at=now,
                duration_s=duration_s,
                participating_clients=num_clients,
                total_clients=total_clients,
                accuracy=global_accuracy,
                loss=global_loss,
                f1=global_f1,
                model_version=f"v{round_number}.0",
                aggregation_method="FedAvg",
            )
            session.add(tr)
            await session.flush()
            round_id = tr.id

        # Insert client participations
        for cm in client_metrics:
            cp = ClientParticipation(
                round_id=round_id,
                org_id=cm.get("org_id", "unknown"),
                status="completed",
                local_accuracy=cm.get("local_accuracy"),
                local_loss=cm.get("local_loss"),
                samples_used=cm.get("samples_used"),
                duration_s=int(cm.get("duration_s", 0)),
                update_size_mb=2.4,  # approximate
            )
            session.add(cp)

        await session.commit()
        logger.info(f"Round {round_number} saved to database (id={round_id})")


# ── Custom FedAvg strategy ─────────────────────────────────────

class SaveMetricsFedAvg(fl.server.strategy.FedAvg):
    """
    Extends FedAvg to:
    1. Collect per-client training metrics from fit results.
    2. Evaluate the aggregated model on a held-out server-side dataset.
    3. Persist everything into the SQLite database.
    """

    def __init__(self, total_clients: int = 3, round_offset: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.total_clients = total_clients
        self.round_offset = round_offset  # offset so FL round 1 -> DB round 13 etc.
        self.round_start_time: float = 0.0
        self.current_round_client_metrics: list[dict] = []

        # Server-side evaluation data (independent test set)
        _, self.server_test_loader, _ = load_partition(
            partition_id=0, num_partitions=1, n_samples=3000, seed=99
        )
        self.eval_model = ThreatNet()

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """Aggregate and collect per-client metrics."""
        self.round_start_time = time.time()
        self.current_round_client_metrics = []

        # Collect client metrics
        for _, fit_res in results:
            metrics = fit_res.metrics or {}
            self.current_round_client_metrics.append(metrics)

        # Standard FedAvg aggregation
        aggregated_params, aggregated_metrics = super().aggregate_fit(
            server_round, results, failures
        )

        if aggregated_params is not None:
            # Evaluate the aggregated model on server-side data
            ndarrays = parameters_to_ndarrays(aggregated_params)
            set_parameters(self.eval_model, ndarrays)
            loss, accuracy, f1, _ = test_model(
                self.eval_model, self.server_test_loader
            )

            duration_s = int(time.time() - self.round_start_time)

            # Actual DB round number = FL round + offset
            db_round = server_round + self.round_offset

            logger.info(
                f"Round {server_round} (DB round {db_round}) aggregated: "
                f"acc={accuracy:.4f}, loss={loss:.4f}, f1={f1:.4f}, "
                f"clients={len(results)}, duration={duration_s}s"
            )

            # Persist to database
            _save_round_to_db(
                round_number=db_round,
                global_accuracy=round(accuracy * 100, 2),
                global_loss=round(loss, 4),
                global_f1=round(f1 * 100, 2),
                duration_s=duration_s,
                num_clients=len(results),
                total_clients=self.total_clients,
                client_metrics=self.current_round_client_metrics,
            )

            aggregated_metrics["global_accuracy"] = accuracy
            aggregated_metrics["global_loss"] = loss
            aggregated_metrics["global_f1"] = f1

        return aggregated_params, aggregated_metrics


# ── Server entry point ─────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Flower FL Server")
    parser.add_argument(
        "--rounds", type=int, default=5,
        help="Number of federated learning rounds (default: 5)",
    )
    parser.add_argument(
        "--min-clients", type=int, default=3,
        help="Minimum number of clients per round (default: 3)",
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Flower server port (default: 8080)",
    )
    args = parser.parse_args()

    # Determine round offset from existing DB rounds
    max_existing = _get_max_round_from_db()
    logger.info(f"Highest existing round in DB: {max_existing}")
    logger.info(f"FL rounds will be numbered {max_existing + 1} to {max_existing + args.rounds}")

    # Create initial model parameters
    init_model = ThreatNet()
    init_params = ndarrays_to_parameters(get_parameters(init_model))

    strategy = SaveMetricsFedAvg(
        total_clients=args.min_clients,
        round_offset=max_existing,
        fraction_fit=1.0,         # Use all available clients
        fraction_evaluate=0.0,    # Disable client-side distributed evaluate
        min_fit_clients=args.min_clients,
        min_available_clients=args.min_clients,
        initial_parameters=init_params,
        on_fit_config_fn=lambda rnd: {"local_epochs": 2},
    )

    logger.info(
        f"Starting Flower server on port {args.port} "
        f"for {args.rounds} rounds (min {args.min_clients} clients)"
    )

    fl.server.start_server(
        server_address=f"0.0.0.0:{args.port}",
        config=fl.server.ServerConfig(num_rounds=args.rounds),
        strategy=strategy,
    )

    logger.info("Federated learning complete.")


if __name__ == "__main__":
    main()
