from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PostIssuanceApplication(Base):
    __tablename__ = "post_issuance_application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    source_certificate_id: Mapped[int] = mapped_column(
        ForeignKey("certificate.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_certificate_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_application_id: Mapped[int] = mapped_column(
        ForeignKey("cert_application.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_application_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    initiator_role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    applicant_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    applicant_username: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_certificate: Mapped["Certificate"] = relationship(back_populates="post_issuance_applications")
    status_history: Mapped[list["PostIssuanceStatusHistory"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="PostIssuanceStatusHistory.changed_at",
    )


class PostIssuanceStatusHistory(Base):
    __tablename__ = "post_issuance_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_issuance_application_id: Mapped[int] = mapped_column(
        ForeignKey("post_issuance_application.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    changed_by_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    application: Mapped[PostIssuanceApplication] = relationship(back_populates="status_history")
