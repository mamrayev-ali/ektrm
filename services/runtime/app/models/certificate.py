from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Certificate(Base):
    __tablename__ = "certificate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certificate_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    source_application_id: Mapped[int] = mapped_column(
        ForeignKey("cert_application.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    source_application_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    applicant_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    applicant_username: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_application: Mapped["CertApplication"] = relationship(back_populates="certificate")
    status_history: Mapped[list["CertificateStatusHistory"]] = relationship(
        back_populates="certificate",
        cascade="all, delete-orphan",
        order_by="CertificateStatusHistory.changed_at",
    )


class CertificateStatusHistory(Base):
    __tablename__ = "certificate_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("certificate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    changed_by_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    certificate: Mapped[Certificate] = relationship(back_populates="status_history")
