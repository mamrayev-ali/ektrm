from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.reference_data import AccreditationAttestat, OpsRegistry, ReferenceDictionary, ReferenceDictionaryItem


class ReferenceDataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_dictionaries(self) -> list[dict[str, object]]:
        items_count = (
            select(
                ReferenceDictionaryItem.dictionary_id.label("dictionary_id"),
                func.count(ReferenceDictionaryItem.id).label("items_count"),
            )
            .group_by(ReferenceDictionaryItem.dictionary_id)
            .subquery()
        )
        stmt = (
            select(
                ReferenceDictionary.code,
                ReferenceDictionary.name,
                ReferenceDictionary.description,
                ReferenceDictionary.is_active,
                func.coalesce(items_count.c.items_count, 0).label("items_count"),
            )
            .outerjoin(items_count, items_count.c.dictionary_id == ReferenceDictionary.id)
            .order_by(ReferenceDictionary.code.asc())
        )
        rows = self._session.execute(stmt).all()
        return [
            {
                "code": row.code,
                "name": row.name,
                "description": row.description,
                "is_active": row.is_active,
                "items_count": int(row.items_count),
            }
            for row in rows
        ]

    def list_dictionary_items(self, dictionary_code: str) -> list[dict[str, object]]:
        stmt: Select[tuple[str, str, int, bool, str | None]] = (
            select(
                ReferenceDictionaryItem.code,
                ReferenceDictionaryItem.name,
                ReferenceDictionaryItem.sort_order,
                ReferenceDictionaryItem.is_active,
                ReferenceDictionaryItem.legal_basis,
            )
            .join(ReferenceDictionary, ReferenceDictionaryItem.dictionary_id == ReferenceDictionary.id)
            .where(ReferenceDictionary.code == dictionary_code)
            .order_by(ReferenceDictionaryItem.sort_order.asc(), ReferenceDictionaryItem.code.asc())
        )
        rows = self._session.execute(stmt).all()
        return [
            {
                "code": row.code,
                "name": row.name,
                "sort_order": row.sort_order,
                "is_active": row.is_active,
                "legal_basis": row.legal_basis,
            }
            for row in rows
        ]

    def list_ops_registry(self, limit: int, search: str | None) -> list[dict[str, object]]:
        stmt = select(
            OpsRegistry.ops_code,
            OpsRegistry.full_name,
            OpsRegistry.bin,
            OpsRegistry.accreditation_attestat_number,
            OpsRegistry.head_name,
            OpsRegistry.city,
            OpsRegistry.is_active,
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                OpsRegistry.full_name.ilike(pattern)
                | OpsRegistry.ops_code.ilike(pattern)
                | OpsRegistry.bin.ilike(pattern)
            )
        rows = self._session.execute(stmt.order_by(OpsRegistry.ops_code.asc()).limit(limit)).all()
        return [
            {
                "ops_code": row.ops_code,
                "full_name": row.full_name,
                "bin": row.bin,
                "accreditation_attestat_number": row.accreditation_attestat_number,
                "head_name": row.head_name,
                "city": row.city,
                "is_active": row.is_active,
            }
            for row in rows
        ]

    def list_accreditation_attestats(self, limit: int, search: str | None) -> list[dict[str, object]]:
        stmt = select(
            AccreditationAttestat.attestat_number,
            AccreditationAttestat.ops_code,
            AccreditationAttestat.issued_at,
            AccreditationAttestat.expires_at,
            AccreditationAttestat.status,
            AccreditationAttestat.scope_summary,
            AccreditationAttestat.is_active,
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                AccreditationAttestat.attestat_number.ilike(pattern)
                | AccreditationAttestat.ops_code.ilike(pattern)
                | AccreditationAttestat.scope_summary.ilike(pattern)
            )
        rows = self._session.execute(stmt.order_by(AccreditationAttestat.attestat_number.asc()).limit(limit)).all()
        return [
            {
                "attestat_number": row.attestat_number,
                "ops_code": row.ops_code,
                "issued_at": row.issued_at.isoformat(),
                "expires_at": row.expires_at.isoformat(),
                "status": row.status,
                "scope_summary": row.scope_summary,
                "is_active": row.is_active,
            }
            for row in rows
        ]
