"""Organization ORM model."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participation_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    local_model_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    local_model_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_update: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    joined_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    privacy_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="Model updates only")
    # JSON-serialised list of DataSlice dicts
    data_distribution_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Relationships
    participations: Mapped[list[ClientParticipation]] = relationship(
        "ClientParticipation", back_populates="organization", cascade="all, delete-orphan"
    )
    threat_detections: Mapped[list[ThreatDetection]] = relationship(
        "ThreatDetection", back_populates="organization", cascade="all, delete-orphan"
    )
    metrics: Mapped[list[Metric]] = relationship(
        "Metric", back_populates="organization", cascade="all, delete-orphan"
    )
    privacy_events: Mapped[list[PrivacyEvent]] = relationship(
        "PrivacyEvent", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} status={self.status!r}>"


# Local imports to avoid circular refs at type-check time
from app.models.client_participation import ClientParticipation  # noqa: E402
from app.models.threat_detection import ThreatDetection  # noqa: E402
from app.models.metric import Metric  # noqa: E402
from app.models.privacy_event import PrivacyEvent  # noqa: E402
