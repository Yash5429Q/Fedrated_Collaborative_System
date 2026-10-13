"""PrivacyEvent ORM model — security events and update validation records."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class PrivacyEvent(Base):
    __tablename__ = "privacy_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")

    organization: Mapped[Organization | None] = relationship(
        "Organization", back_populates="privacy_events"
    )

    def __repr__(self) -> str:
        return f"<PrivacyEvent id={self.id!r} severity={self.severity!r}>"


from app.models.organization import Organization  # noqa: E402
