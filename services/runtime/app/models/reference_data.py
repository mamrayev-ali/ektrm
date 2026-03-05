from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReferenceDictionary(Base):
    __tablename__ = "reference_dictionaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    items: Mapped[list["ReferenceDictionaryItem"]] = relationship(
        back_populates="dictionary", cascade="all, delete-orphan"
    )


class ReferenceDictionaryItem(Base):
    __tablename__ = "reference_dictionary_items"
    __table_args__ = (
        UniqueConstraint("dictionary_id", "code", name="uq_reference_dictionary_item_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dictionary_id: Mapped[int] = mapped_column(
        ForeignKey("reference_dictionaries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))
    legal_basis: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    dictionary: Mapped[ReferenceDictionary] = relationship(back_populates="items")


class OpsRegistry(Base):
    __tablename__ = "ops_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ops_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    bin: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    accreditation_attestat_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    head_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AccreditationAttestat(Base):
    __tablename__ = "accreditation_attestats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attestat_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ops_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
