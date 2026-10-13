"""TrainingRound ORM model."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class TrainingRound(Base):
    __tablename__ = "training_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    started_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    completed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participating_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    f1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    aggregation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="FedAvg")

    # Relationships
    participations: Mapped[list[ClientParticipation]] = relationship(
        "ClientParticipation", back_populates="training_round", cascade="all, delete-orphan"
    )
    model_versions: Mapped[list[ModelVersion]] = relationship(
        "ModelVersion", back_populates="training_round", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TrainingRound round={self.round_number} status={self.status!r}>"


from app.models.client_participation import ClientParticipation  # noqa: E402
from app.models.model_version import ModelVersion  # noqa: E402
