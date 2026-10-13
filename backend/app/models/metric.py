"""Metric ORM model — stores per-round and per-org performance metrics."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False, default="federated")
    org_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    round_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    organization: Mapped[Organization | None] = relationship(
        "Organization", back_populates="metrics"
    )

    def __repr__(self) -> str:
        return f"<Metric name={self.metric_name!r} value={self.metric_value} type={self.model_type!r}>"


from app.models.organization import Organization  # noqa: E402
