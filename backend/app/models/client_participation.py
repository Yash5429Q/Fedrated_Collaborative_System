"""ClientParticipation ORM model — bridge between organizations and training rounds."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ClientParticipation(Base):
    __tablename__ = "client_participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("training_rounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    local_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    local_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    samples_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    update_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    training_round: Mapped[TrainingRound] = relationship(
        "TrainingRound", back_populates="participations"
    )
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="participations"
    )

    def __repr__(self) -> str:
        return f"<ClientParticipation round_id={self.round_id} org={self.org_id!r} status={self.status!r}>"


from app.models.training_round import TrainingRound  # noqa: E402
from app.models.organization import Organization  # noqa: E402
