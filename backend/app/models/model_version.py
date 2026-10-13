"""ModelVersion ORM model."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    round_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("training_rounds.id", ondelete="SET NULL"), nullable=True
    )
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    f1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    false_positive_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    training_round: Mapped[TrainingRound | None] = relationship(
        "TrainingRound", back_populates="model_versions"
    )

    def __repr__(self) -> str:
        return f"<ModelVersion version={self.version!r} accuracy={self.accuracy}>"


from app.models.training_round import TrainingRound  # noqa: E402
