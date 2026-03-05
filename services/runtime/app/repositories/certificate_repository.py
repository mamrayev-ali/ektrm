from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateRegistryPublication, CertificateStatusHistory


class CertificateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_certificate(self, certificate_id: int) -> Certificate | None:
        return self._session.get(Certificate, certificate_id)

    def get_by_source_application(self, application_id: int) -> Certificate | None:
        stmt = select(Certificate).where(Certificate.source_application_id == application_id)
        return self._session.scalar(stmt)

    def list_internal_registry(
        self,
        limit: int,
        offset: int,
        search: str | None,
        applicant_subject: str | None = None,
    ) -> list[Certificate]:
        stmt = select(Certificate)
        if applicant_subject:
            stmt = stmt.where(Certificate.applicant_subject == applicant_subject)
        if search:
            like_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Certificate.certificate_number.ilike(like_pattern),
                    Certificate.source_application_number.ilike(like_pattern),
                )
            )
        stmt = stmt.order_by(
            Certificate.updated_at.desc(),
            Certificate.generated_at.desc(),
            Certificate.id.desc(),
        ).limit(limit).offset(offset)
        return list(self._session.scalars(stmt).all())

    def list_public_registry(self, limit: int, offset: int, search: str | None) -> list[Certificate]:
        stmt = select(Certificate).where(Certificate.published_at.is_not(None))
        if search:
            like_pattern = f"%{search.strip()}%"
            stmt = stmt.where(Certificate.certificate_number.ilike(like_pattern))
        stmt = stmt.order_by(
            Certificate.published_at.desc(),
            Certificate.updated_at.desc(),
            Certificate.id.desc(),
        ).limit(limit).offset(offset)
        return list(self._session.scalars(stmt).all())

    def create_certificate(
        self,
        certificate_number: str,
        source_application_id: int,
        source_application_number: str,
        applicant_subject: str,
        applicant_username: str,
        snapshot: dict[str, Any],
        generated_by_subject: str,
    ) -> Certificate:
        certificate = Certificate(
            certificate_number=certificate_number,
            source_application_id=source_application_id,
            source_application_number=source_application_number,
            status="GENERATED",
            applicant_subject=applicant_subject,
            applicant_username=applicant_username,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            generated_by_subject=generated_by_subject,
        )
        self._session.add(certificate)
        self._session.flush()
        return certificate

    def add_history(
        self,
        certificate_id: int,
        from_status: str | None,
        to_status: str,
        changed_by_subject: str,
        comment: str | None,
    ) -> None:
        row = CertificateStatusHistory(
            certificate_id=certificate_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_subject=changed_by_subject,
            comment=comment,
        )
        self._session.add(row)

    def add_publication(
        self,
        certificate_id: int,
        visibility: str,
        is_public: bool,
        published_by_subject: str,
        comment: str | None,
    ) -> None:
        row = CertificateRegistryPublication(
            certificate_id=certificate_id,
            visibility=visibility,
            is_public=is_public,
            published_by_subject=published_by_subject,
            comment=comment,
        )
        self._session.add(row)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
