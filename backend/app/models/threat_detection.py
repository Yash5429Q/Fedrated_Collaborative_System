"""ThreatDetection ORM model."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ThreatDetection(Base):
    __tablename__ = "threat_detections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    threat_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False, default="")
    destination_ip: Mapped[str] = mapped_column(String(45), nullable=False, default="")
    protocol: Mapped[str] = mapped_column(String(8), nullable=False, default="TCP")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_features_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    detection_method: Mapped[str] = mapped_column(String(16), nullable=False, default="federated")

    organization: Mapped[Organization | None] = relationship(
        "Organization", back_populates="threat_detections"
    )

    def __repr__(self) -> str:
        return f"<ThreatDetection id={self.id!r} type={self.threat_type!r} severity={self.severity!r}>"


from app.models.organization import Organization  # noqa: E402
